package com.deccan.onboardiq;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.DefaultApplicationArguments;
import org.springframework.jdbc.core.JdbcTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import com.deccan.onboardiq.seed.ReferenceDataSeeder;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Phase 1 gate: app boots on PostgreSQL 16, Flyway migrates, seeding is complete and idempotent, audit is append-only. */
@Testcontainers
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "onboardiq.data-dir=../../data")
class SchemaAndSeedIT {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16");

    @Autowired JdbcTemplate jdbc;
    @Autowired TestRestTemplate http;
    @Autowired ReferenceDataSeeder seeder;

    private long count(String table) {
        return jdbc.queryForObject("SELECT count(*) FROM " + table, Long.class);
    }

    @Test
    void referenceDataAndUsersAreSeeded() {
        assertThat(count("occupations")).isEqualTo(12);
        assertThat(count("sanctions_entries")).isEqualTo(50);
        assertThat(count("pep_entries")).isEqualTo(60);
        assertThat(count("existing_customers")).isEqualTo(300);
        assertThat(count("users")).isEqualTo(5);
        assertThat(jdbc.queryForList("SELECT role FROM user_roles r JOIN users u ON u.id = r.user_id WHERE u.username = 'u1'", String.class))
                .containsExactlyInAnyOrder("KYC_OFFICER", "COMPLIANCE_OFFICER");
    }

    @Test
    void rulesConfigComesFromTheJsonFilePlusTeamKeys() {
        assertThat(jdbc.queryForObject("SELECT (value #>> '{}')::numeric FROM rules_config WHERE key='name_match_threshold'", Double.class)).isEqualTo(0.9);
        assertThat(jdbc.queryForObject("SELECT value->>'HIGH' FROM rules_config WHERE key='rekyc_years'", String.class)).isEqualTo("2");
        assertThat(jdbc.queryForObject("SELECT value #>> '{}' FROM rules_config WHERE key='routing.auto_reject_enabled'", String.class)).isEqualTo("true");
        assertThat(jdbc.queryForObject("SELECT value #>> '{}' FROM rules_config WHERE key='duplicate.check_open_applications'", String.class)).isEqualTo("true");
        assertThat(count("rules_config")).isEqualTo(19); // 17 keys in the file + 2 team keys
    }

    @Test
    void seedingTwiceChangesNothing() throws Exception {
        ApplicationArguments none = new DefaultApplicationArguments();
        seeder.run(none);
        assertThat(count("users")).isEqualTo(5);
        assertThat(count("sanctions_entries")).isEqualTo(50);
        assertThat(count("rules_config")).isEqualTo(19);
        assertThat(count("rules_config_history")).isEqualTo(1);
    }

    @Test
    void auditLogIsAppendOnly() {
        jdbc.update("INSERT INTO audit_log(action, details) VALUES ('CONFIG_CHANGED', '{}'::jsonb)");
        assertThatThrownBy(() -> jdbc.update("UPDATE audit_log SET action = 'STATUS_CHANGED'"))
                .hasMessageContaining("append-only");
        assertThatThrownBy(() -> jdbc.update("DELETE FROM audit_log"))
                .hasMessageContaining("append-only");
        assertThatThrownBy(() -> jdbc.execute("TRUNCATE audit_log"))
                .hasMessageContaining("append-only");
    }

    @Test
    @SuppressWarnings("unchecked")
    void healthEndpointIsUp() {
        Map<String, Object> body = http.getForObject("/api/v1/health", Map.class);
        assertThat(body).containsEntry("status", "UP").containsEntry("config_version", "1.0");
    }
}
