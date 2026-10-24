package com.deccan.onboardiq.health;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Lightweight health endpoint for docker-compose health checks and the demo.
 * Spring Actuator's /actuator/health is also exposed.
 */
@RestController
@RequestMapping("/api/v1")
public class HealthController {

    private final JdbcTemplate jdbc;
    private final Clock clock;

    public HealthController(JdbcTemplate jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "UP");
        body.put("time", OffsetDateTime.now(clock).toString());
        try {
            body.put("db", "UP");
            body.put("config_version", jdbc.queryForObject(
                    "SELECT value #>> '{}' FROM rules_config WHERE key = 'version'", String.class));
            Map<String, Object> counts = new LinkedHashMap<>();
            for (String t : new String[]{"occupations", "sanctions_entries", "pep_entries", "existing_customers", "users"}) {
                counts.put(t, jdbc.queryForObject("SELECT count(*) FROM " + t, Long.class));
            }
            body.put("reference_data", counts);
        } catch (Exception e) {
            body.put("status", "DEGRADED");
            body.put("db", "DOWN");
        }
        return body;
    }
}
