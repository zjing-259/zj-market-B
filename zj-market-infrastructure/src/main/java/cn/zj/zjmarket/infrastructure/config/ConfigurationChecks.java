package cn.zj.zjmarket.infrastructure.config;

final class ConfigurationChecks {
    private ConfigurationChecks() { }
    static void required(String value, String name) {
        if (value == null || value.isBlank()) throw new IllegalStateException("Missing external configuration: " + name);
    }
    static void require(boolean valid, String reason) {
        if (!valid) throw new IllegalStateException(reason);
    }
}
