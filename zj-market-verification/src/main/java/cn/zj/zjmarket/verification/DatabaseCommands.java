package cn.zj.zjmarket.verification;

import cn.zj.zjmarket.ZjMarketApplication;
import cn.zj.zjmarket.infrastructure.config.properties.DatabaseSettings;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import javax.sql.DataSource;
import org.flywaydb.core.Flyway;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
/** Explicit maintenance commands. Not included in the normal app executable. */
public final class DatabaseCommands {
    private DatabaseCommands() {}
    private static String schema(){
        String scope=System.getenv("B_DATABASE_SCOPE");
        if(scope==null || scope.equals("development"))return "zj_market";
        if(scope.equals("b02-test"))return "zj_market_b02_test";
        throw new IllegalArgumentException("Unsupported explicit database scope");
    }
    private static String runtimeUser(){return schema().equals("zj_market")?"zj_market_app":"zj_market_b02_test_app";}
    private static String migrationUser(){return schema().equals("zj_market")?"zj_market_migrator":"zj_market_b02_test_migrator";}

    public static int run(String mode) {
        try {
            if (!List.of("migrate", "verify").contains(mode)) {
                throw new IllegalArgumentException("Supported database commands: migrate, verify");
            }
            String user = required(mode.equals("migrate") ? "B_MIGRATION_USERNAME" : "B_DATABASE_USERNAME");
            String password = required(mode.equals("migrate") ? "B_MIGRATION_PASSWORD" : "B_DATABASE_PASSWORD");
            String expected = mode.equals("migrate") ? migrationUser() : runtimeUser();
            if (!user.equals(expected)) throw new IllegalArgumentException("Wrong database account for command");
            String url = required("B_DATABASE_URL");
            var settings = new DatabaseSettings();
            settings.setUrl(url);
            settings.setUsername(user);
            settings.setPassword(password);
            settings.validate();
            if (!url.matches("^jdbc:mysql://[^/]+/" + schema() + "(?:\\?.*)?$")) {
                throw new IllegalArgumentException("Maintenance commands only target zj_market");
            }
            List<String> evidence = new ArrayList<>();
            evidence.add("java=" + Runtime.version());
            if (mode.equals("migrate")) {
                Flyway flyway = Flyway.configure()
                        .dataSource(url, user, password)
                        .defaultSchema(schema())
                        .schemas(schema())
                        .createSchemas(false)
                        .cleanDisabled(true)
                        .baselineOnMigrate(false)
                        .locations("classpath:db/migration").load();
                var result = flyway.migrate();
                flyway.validate();
                var metadata = new java.util.Properties();
                try (var resource = Flyway.class.getResourceAsStream("/META-INF/maven/org.flywaydb/flyway-core/pom.properties")) {
                    if (resource == null) throw new IllegalStateException("Missing Flyway version metadata");
                    metadata.load(resource);
                }
                evidence.add("flyway=" + metadata.getProperty("version"));
                evidence.add("migrationsExecuted=" + result.migrationsExecuted);
                try (Connection c = java.sql.DriverManager.getConnection(url, user, password)) {
                    identity(c, evidence);
                    migrationBoundary(c, evidence);
                }
            } else {
                // Use the actual normal B bootstrap and Hikari datasource, with adapters disabled.
                SpringApplication application = new SpringApplication(ZjMarketApplication.class);
                application.setWebApplicationType(WebApplicationType.NONE);
                try (var context = application.run(
                        "--b.infrastructure.database.enabled=true","--b.trial.enabled=false","--b.sync.enabled=false","--b.identity.enabled=false","--b.product.enabled=false","--b.inventory.enabled=false","--b.order.enabled=false","--b.trade.enabled=false","--b.payment.enabled=false","--b.trade.events-enabled=false",
                        "--b.infrastructure.rpc.enabled=false", "--b.infrastructure.mq.enabled=false")) {
                    var bound = context.getBean(DatabaseSettings.class);
                    if (!bound.getUsername().equals(runtimeUser()) || !bound.getUrl().equals(url)) {
                        throw new IllegalStateException("Unexpected datasource configuration");
                    }
                    try (Connection c = context.getBean(DataSource.class).getConnection()) {
                        identity(c, evidence);
                        runtimeBoundary(c, evidence);
                    }
                }
            }
            evidence.add("status=PASSED");
            String report = required("B_DATABASE_REPORT");
            Path output = Path.of(report).toAbsolutePath();
            Files.createDirectories(output.getParent());
            Files.write(output, evidence);
            System.out.println("B database " + mode + ": PASSED");
            return 0;
        } catch (Exception e) {
            // Never render credentials, connection properties or arbitrary JDBC error text.
            String failure = "status=FAILED\nerror=" + e.getClass().getSimpleName();
            for (Throwable cause = e; cause != null; cause = cause.getCause()) {
                if (cause instanceof SQLException sql) {
                    failure += "\nsqlError=" + sql.getErrorCode() + "\nsqlState=" + sql.getSQLState();
                }
            }
            String report = System.getenv("B_DATABASE_REPORT");
            if (report != null) {
                try { Files.writeString(Path.of(report), failure + "\n"); }
                catch (java.io.IOException ignored) { /* Return failure even if report cannot be written. */ }
            }
            System.err.println("B database command failed: " + e.getClass().getSimpleName());
            return 1;
        }
    }

    private static String required(String key) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) throw new IllegalArgumentException("Missing " + key);
        return value;
    }

    private static void identity(Connection c, List<String> evidence) throws SQLException {
        try (var s = c.createStatement(); var rs = s.executeQuery(
                "SELECT VERSION(), DATABASE(), CURRENT_USER()")) {
            rs.next();
            if (!schema().equals(rs.getString(2))) throw new IllegalStateException("Wrong schema");
            evidence.add("mysql=" + rs.getString(1));
            evidence.add("schema=" + rs.getString(2));
            evidence.add("account=" + rs.getString(3));
        }
    }

    private static void runtimeBoundary(Connection c, List<String> evidence) throws SQLException {
        String id = UUID.randomUUID().toString();
        c.setAutoCommit(false);
        try {
            try (var p = c.prepareStatement("INSERT INTO b_database_probe VALUES (?,?)")) {
                p.setString(1, id); p.setString(2, "initial"); requireOne(p.executeUpdate());
            }
            try (var p = c.prepareStatement("UPDATE b_database_probe SET probe_value=? WHERE probe_id=?")) {
                p.setString(1, "updated"); p.setString(2, id); requireOne(p.executeUpdate());
            }
            try (var p = c.prepareStatement("SELECT probe_value FROM b_database_probe WHERE probe_id=?")) {
                p.setString(1, id);
                try (var rs = p.executeQuery()) {
                    if (!rs.next() || !"updated".equals(rs.getString(1))) throw new IllegalStateException("CRUD mismatch");
                }
            }
            try (var p = c.prepareStatement("DELETE FROM b_database_probe WHERE probe_id=?")) {
                p.setString(1, id); requireOne(p.executeUpdate());
            }
        } finally { c.rollback(); c.setAutoCommit(true); }
        evidence.add("runtimeCRUD=PASSED (rolled back)");
        // Inert statements where possible; the account's DDL privileges are also checked below.
        denied(c, "CREATE TABLE " + schema() + ".b_forbidden_probe (id INT)", 1142);
        denied(c, "DROP TABLE IF EXISTS " + schema() + ".b_absent_" + UUID.randomUUID().toString().replace("-", ""), 1142);
        denied(c, "ALTER TABLE " + schema() + ".b_database_probe COMMENT=''", 1142);
        denied(c, "SELECT * FROM " + schema() + ".flyway_schema_history LIMIT 0", 1142);
        denied(c, "UPDATE " + schema() + ".flyway_schema_history SET success=success WHERE 1=0", 1142);
        sharedDenials(c);
        try (var s = c.createStatement(); var rs = s.executeQuery("SHOW GRANTS")) {
            while (rs.next()) {
                String grant = rs.getString(1);
                if (!grant.startsWith("GRANT USAGE ON *.* TO ")
                        && !allowedRuntimeGrant(grant)) {
                    throw new IllegalStateException("Unexpected runtime grant");
                }
                if (grant.contains("WITH GRANT OPTION")) throw new IllegalStateException("Grant option detected");
                evidence.add("grant=" + grant);
            }
        }
        evidence.add("runtimeDDL/history/A/system/grant=DENIED");
    }

    private static void migrationBoundary(Connection c, List<String> evidence) throws SQLException {
        String table = "b_migration_probe_" + UUID.randomUUID().toString().replace("-", "");
        try (Statement s = c.createStatement()) {
            s.execute("CREATE TABLE " + schema() + "." + table + " (id INT PRIMARY KEY)");
            try {
                s.execute("ALTER TABLE " + schema() + "." + table + " ADD COLUMN marker INT");
                s.execute("CREATE INDEX idx_marker ON " + schema() + "." + table + " (marker)");
                s.execute("INSERT INTO " + schema() + "." + table + " VALUES (1,2)");
                s.execute("UPDATE " + schema() + "." + table + " SET marker=3 WHERE id=1");
                s.execute("DELETE FROM " + schema() + "." + table + " WHERE id=1");
            } finally { s.execute("DROP TABLE " + schema() + "." + table); }
        }
        sharedDenials(c);
        denied(c, "CREATE DATABASE b_forbidden_schema_probe", 1044);
        try (var s = c.createStatement(); var rs = s.executeQuery("SHOW GRANTS")) {
            while (rs.next()) {
                String grant = rs.getString(1);
                if (!grant.startsWith("GRANT USAGE ON *.* TO ")
                        && !grant.matches("GRANT [A-Z, ]+ ON `"+schema()+"`\\.\\* TO .*")) {
                    throw new IllegalStateException("Unexpected migration grant");
                }
                if (grant.contains("WITH GRANT OPTION")) throw new IllegalStateException("Grant option detected");
                evidence.add("grant=" + grant);
            }
        }
        evidence.add("migrationDDL=PASSED (temporary table removed)");
        evidence.add("migrationA/system/globalDDL/grant=DENIED");
    }

    private static void sharedDenials(Connection c) throws SQLException {
        denied(c, "USE " + (schema().equals("zj_market")?"zj_market_b02_test":"zj_market"), 1044);
        denied(c, "USE group_buy_market", 1044);
        denied(c, "USE group_buy_market_phase1_test", 1044);
        denied(c, "SELECT User FROM mysql.user LIMIT 0", 1142);
        // Granting access to the B probe requires GRANT OPTION; both accounts must be denied.
        denied(c, "GRANT SELECT ON "+schema()+".b_database_probe TO '"+runtimeUser()+"'@'%'", 1142, 1044);
    }

    private static void denied(Connection c, String sql, int... codes) throws SQLException {
        try (Statement s = c.createStatement()) { s.execute(sql); }
        catch (SQLException e) {
            for (int code : codes) if (e.getErrorCode() == code && e.getSQLState().startsWith("42")) return;
            throw new IllegalStateException("Negative permission test returned unexpected SQL error code " + e.getErrorCode());
        }
        throw new IllegalStateException("Negative permission test unexpectedly succeeded");
    }

    private static boolean allowedRuntimeGrant(String grant){
        for(String table:List.of("b_database_probe","b_user","b_user_role","b_login_grant","b_refresh_token","b_product","b_product_outbox","b_product_sync","b_sync_inbox","b_sync_quarantine","b_sync_audit","b_inventory_account","b_inventory_operation","b_inventory_ledger","b_purchase_confirmation","b_purchase_guard","b_market_order","b_inventory_reservation","b_trade_coordination","b_trade_attempt","b_order_operation","b_payment","b_payment_attempt","b_payment_operation","b_payment_task","b_sim_payment","b_sim_attempt","b_sim_operation","b_sim_notification","b_trade_outbox","b_trade_inbox","b_trade_quarantine","b_trade_work","b_team_cursor","b_fulfillment","b_reconciliation_task","b_reconciliation_member","b_reconciliation_submission","b_refund","b_trade_evidence_link","b_order_block","b_refund_attempt","b_refund_task","b_sim_refund","b_sim_refund_attempt","b_sim_refund_notification","b_refund_release","b_refund_operation"))
            if(grant.startsWith("GRANT SELECT, INSERT, UPDATE, DELETE ON `"+schema()+"`.`"+table+"` TO "))return true;
        return false;
    }
    private static void requireOne(int affected) {
        if (affected != 1) throw new IllegalStateException("Unexpected affected rows");
    }
}