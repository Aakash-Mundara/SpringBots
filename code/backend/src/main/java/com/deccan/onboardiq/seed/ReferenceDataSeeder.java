package com.deccan.onboardiq.seed;

import com.deccan.onboardiq.common.CsvReader;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.BooleanNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Date;
import java.time.LocalDate;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Idempotent first-start seeding (Section 3.1).
 *
 * <ul>
 *   <li>rules_config: one row per top-level key of case_02_rules_config_V1.0.json, inserted with
 *       ON CONFLICT DO NOTHING so admin edits survive restarts while new keys are picked up.
 *       Two team keys are added: routing.auto_reject_enabled=true and
 *       duplicate.check_open_applications=true.</li>
 *   <li>occupations / sanctions / PEP / existing customers: loaded only when the table is empty,
 *       so a watchlist replaced through the admin API is never silently re-populated.</li>
 *   <li>demo users: inserted when the username is absent.</li>
 * </ul>
 */
@Component
@Order(10)
public class ReferenceDataSeeder implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(ReferenceDataSeeder.class);

    /** Team keys that are not in the case-study file (Sections 3.1, 6.2, 6.6). */
    static final Map<String, JsonNode> TEAM_DEFAULT_KEYS = Map.of(
            "routing.auto_reject_enabled", BooleanNode.TRUE,
            "duplicate.check_open_applications", BooleanNode.TRUE);

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;
    private final SeedProperties props;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

    public ReferenceDataSeeder(JdbcTemplate jdbc, ObjectMapper mapper, SeedProperties props) {
        this.jdbc = jdbc;
        this.mapper = mapper;
        this.props = props;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) throws Exception {
        if (!props.enabled()) {
            log.info("Seeding disabled (SEED_ENABLED=false)");
            return;
        }
        seedRulesConfig();
        seedOccupations();
        seedSanctions();
        seedPep();
        seedExistingCustomers();
        seedDemoUsers();
    }

    // ------------------------------------------------------------------ rules_config
    void seedRulesConfig() throws IOException {
        Path file = Path.of(props.rulesConfigFile());
        ObjectNode root = (ObjectNode) mapper.readTree(Files.readString(file));
        Map<String, JsonNode> entries = new LinkedHashMap<>();
        for (Iterator<Map.Entry<String, JsonNode>> it = root.fields(); it.hasNext(); ) {
            Map.Entry<String, JsonNode> e = it.next();
            entries.put(e.getKey(), e.getValue());
        }
        TEAM_DEFAULT_KEYS.forEach(entries::putIfAbsent);

        int inserted = 0;
        for (Map.Entry<String, JsonNode> e : entries.entrySet()) {
            inserted += jdbc.update(
                    "INSERT INTO rules_config(key, value, updated_by) VALUES (?, ?::jsonb, 'seed') "
                            + "ON CONFLICT (key) DO NOTHING",
                    e.getKey(), mapper.writeValueAsString(e.getValue()));
        }
        Integer history = jdbc.queryForObject("SELECT count(*) FROM rules_config_history", Integer.class);
        if (history != null && history == 0) {
            ObjectNode snapshot = mapper.createObjectNode();
            entries.forEach(snapshot::set);
            jdbc.update("INSERT INTO rules_config_history(config_version, snapshot, changed_by) VALUES (?, ?::jsonb, 'seed')",
                    root.path("version").asText("1.0"), mapper.writeValueAsString(snapshot));
        }
        log.info("rules_config: {} of {} keys inserted from {}", inserted, entries.size(), file.getFileName());
    }

    // ------------------------------------------------------------------ reference CSVs
    void seedOccupations() throws IOException {
        if (!isEmpty("occupations")) {
            return;
        }
        List<Map<String, String>> rows = CsvReader.readWithHeader(Path.of(props.occupationsFile()));
        for (Map<String, String> r : rows) {
            jdbc.update("INSERT INTO occupations(occupation_code, description, risk_level) VALUES (?,?,?)",
                    r.get("occupation_code"), r.get("description"), r.get("risk_level"));
        }
        log.info("occupations: {} rows loaded", rows.size());
    }

    void seedSanctions() throws IOException {
        if (!isEmpty("sanctions_entries")) {
            return;
        }
        List<Map<String, String>> rows = CsvReader.readWithHeader(Path.of(props.sanctionsFile()));
        for (Map<String, String> r : rows) {
            jdbc.update("INSERT INTO sanctions_entries(list_id, name, alias, dob, nationality, program) VALUES (?,?,?,?,?,?)",
                    r.get("list_id"), r.get("name"), blankToNull(r.get("alias")), date(r.get("dob")),
                    blankToNull(r.get("nationality")), blankToNull(r.get("program")));
        }
        log.info("sanctions_entries: {} rows loaded", rows.size());
    }

    void seedPep() throws IOException {
        if (!isEmpty("pep_entries")) {
            return;
        }
        List<Map<String, String>> rows = CsvReader.readWithHeader(Path.of(props.pepFile()));
        for (Map<String, String> r : rows) {
            jdbc.update("INSERT INTO pep_entries(pep_id, name, dob, position, category) VALUES (?,?,?,?,?)",
                    r.get("pep_id"), r.get("name"), date(r.get("dob")),
                    blankToNull(r.get("position")), blankToNull(r.get("category")));
        }
        log.info("pep_entries: {} rows loaded", rows.size());
    }

    void seedExistingCustomers() throws IOException {
        if (!isEmpty("existing_customers")) {
            return;
        }
        List<Map<String, String>> rows = CsvReader.readWithHeader(Path.of(props.existingCustomersFile()));
        for (Map<String, String> r : rows) {
            jdbc.update("INSERT INTO existing_customers(customer_id, full_name, pan_number, dob) VALUES (?,?,?,?)",
                    r.get("customer_id"), r.get("full_name"), r.get("pan_number"), date(r.get("dob")));
        }
        log.info("existing_customers: {} rows loaded", rows.size());
    }

    // ------------------------------------------------------------------ demo users
    record DemoUser(String username, String displayName, List<String> roles) {
    }

    static final List<DemoUser> DEMO_USERS = List.of(
            new DemoUser("applicant1", "Applicant One", List.of("APPLICANT")),
            new DemoUser("applicant2", "Applicant Two", List.of("APPLICANT")),
            // u1 holds BOTH officer roles so the example-11 403 is proven by the maker≠checker rule,
            // not by a missing role.
            new DemoUser("u1", "Officer U1 (maker + checker roles)", List.of("KYC_OFFICER", "COMPLIANCE_OFFICER")),
            new DemoUser("officer2", "KYC Officer Two", List.of("KYC_OFFICER")),
            new DemoUser("u2", "Compliance Officer U2", List.of("COMPLIANCE_OFFICER")));

    void seedDemoUsers() {
        int created = 0;
        for (DemoUser u : DEMO_USERS) {
            Integer exists = jdbc.queryForObject("SELECT count(*) FROM users WHERE username = ?", Integer.class, u.username());
            if (exists != null && exists > 0) {
                continue;
            }
            UUID id = UUID.randomUUID();
            jdbc.update("INSERT INTO users(id, username, password_hash, display_name, enabled) VALUES (?,?,?,?,TRUE)",
                    id, u.username(), encoder.encode(props.demoPassword()), u.displayName());
            for (String role : u.roles()) {
                jdbc.update("INSERT INTO user_roles(user_id, role) VALUES (?,?)", id, role);
            }
            created++;
        }
        log.info("demo users: {} created", created);
    }

    // ------------------------------------------------------------------ helpers
    private boolean isEmpty(String table) {
        Integer n = jdbc.queryForObject("SELECT count(*) FROM " + table, Integer.class);
        return n == null || n == 0;
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s.trim();
    }

    private static Date date(String s) {
        String v = blankToNull(s);
        return v == null ? null : Date.valueOf(LocalDate.parse(v));
    }
}
