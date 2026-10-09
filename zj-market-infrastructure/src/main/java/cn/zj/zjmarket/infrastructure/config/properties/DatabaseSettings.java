package cn.zj.zjmarket.infrastructure.config.properties;

import org.springframework.boot.context.properties.ConfigurationProperties;
/** Bound external configuration. Deliberately no generated toString containing credentials. */
@ConfigurationProperties("b.infrastructure.database")
public class DatabaseSettings {
    private boolean enabled = false;
    private String url;
    private String username;
    private String password;
    private int maximumPoolSize = 10;
    private long connectionTimeoutMillis = 5000;
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean value) { enabled = value; }
    public String getUrl() { return url; }
    public void setUrl(String value) { url = value; }
    public String getUsername() { return username; }
    public void setUsername(String value) { username = value; }
    public String getPassword() { return password; }
    public void setPassword(String value) { password = value; }
    public int getMaximumPoolSize() { return maximumPoolSize; }
    public void setMaximumPoolSize(int value) { maximumPoolSize = value; }
    public long getConnectionTimeoutMillis() { return connectionTimeoutMillis; }
    public void setConnectionTimeoutMillis(long value) { connectionTimeoutMillis = value; }
    public void validate() {
        ConfigurationChecks.required(url, "database.url");
        // An A datasource inherited by the verification process must never become B's datasource.
        java.util.regex.Matcher schema = java.util.regex.Pattern
                .compile("^jdbc:mysql://[^/]+/([A-Za-z0-9_]+)(?:\\?.*)?$").matcher(url);
        ConfigurationChecks.require(schema.matches()
                && schema.group(1).matches("zj_market(?:_[A-Za-z0-9_]+)?"),
                "B datasource must use a dedicated zj_market schema");
        ConfigurationChecks.required(username, "database.username");
        ConfigurationChecks.required(password, "database.password");
        ConfigurationChecks.require(maximumPoolSize > 0, "Database pool size must be positive");
        ConfigurationChecks.require(connectionTimeoutMillis >= 250, "Database timeout must be at least 250ms");
    }
}
