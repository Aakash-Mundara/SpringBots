package com.deccan.onboardiq.seed;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "onboardiq.seed")
public record SeedProperties(
        boolean enabled,
        String rulesConfigFile,
        String occupationsFile,
        String sanctionsFile,
        String pepFile,
        String existingCustomersFile,
        String demoPassword) {
}
