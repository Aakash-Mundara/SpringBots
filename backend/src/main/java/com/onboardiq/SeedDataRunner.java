package com.onboardiq;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.env.Environment;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Date;
import java.util.Map;

@Component
public class SeedDataRunner implements ApplicationRunner {
  private final JdbcTemplate jdbc;
  private final Environment env;
  private final ObjectMapper mapper = new ObjectMapper();
  private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
  public SeedDataRunner(JdbcTemplate jdbc, Environment env) { this.jdbc = jdbc; this.env = env; }

  @Override public void run(ApplicationArguments args) throws Exception {
    if (java.util.Arrays.asList(env.getActiveProfiles()).contains("batch")) return;
    seedUsers();
    Path data = Path.of(env.getProperty("app.data-dir", "./data"));
    Path rules = data.resolve("case_02_rules_config_V1.0.json");
    if (Files.exists(rules)) {
      Map<?, ?> values = mapper.readValue(rules.toFile(), Map.class);
      for (var entry : values.entrySet()) putConfig(String.valueOf(entry.getKey()), entry.getValue());
    }
    putConfig("routing.auto_reject_enabled", true);
    seedCsv(data.resolve("case_02_occupations_V1.0.csv"), "INSERT INTO occupations(occupation_code,description,risk_level) VALUES (?,?,?) ON CONFLICT (occupation_code) DO UPDATE SET description=EXCLUDED.description,risk_level=EXCLUDED.risk_level", r -> new Object[]{r.get("occupation_code"), r.get("description"), r.get("risk_level")});
    seedCsv(data.resolve("case_02_sanctions_list_V1.0.csv"), "INSERT INTO sanctions_entries(list_id,name,alias,dob,nationality,program) VALUES (?,?,?,?,?,?) ON CONFLICT (list_id) DO NOTHING", r -> new Object[]{r.get("list_id"), r.get("name"), emptyNull(r.get("alias")), date(r.get("dob")), emptyNull(r.get("nationality")), emptyNull(r.get("program"))});
    seedCsv(data.resolve("case_02_pep_list_V1.0.csv"), "INSERT INTO pep_entries(pep_id,name,dob,position,category) VALUES (?,?,?,?,?) ON CONFLICT (pep_id) DO NOTHING", r -> new Object[]{r.get("pep_id"), r.get("name"), date(r.get("dob")), emptyNull(r.get("position")), emptyNull(r.get("category"))});
    seedCsv(data.resolve("case_02_existing_customers_V1.0.csv"), "INSERT INTO existing_customers(customer_id,full_name,pan_number,dob) VALUES (?,?,?,?) ON CONFLICT (customer_id) DO NOTHING", r -> new Object[]{r.get("customer_id"), r.get("full_name"), r.get("pan_number"), date(r.get("dob"))});
  }
  private void seedUsers() {
    String[][] users = {{"applicant1","Applicant One","APPLICANT"},{"applicant2","Applicant Two","APPLICANT"},{"u1","Officer One","KYC_OFFICER,COMPLIANCE_OFFICER"},{"officer2","Officer Two","KYC_OFFICER"},{"u2","Compliance Two","COMPLIANCE_OFFICER"}};
    for (String[] u : users) {
      jdbc.update("INSERT INTO users(username,password_hash,display_name) VALUES (?,?,?) ON CONFLICT(username) DO NOTHING", u[0], encoder.encode("Passw0rd!"), u[1]);
      Long id = jdbc.queryForObject("SELECT id FROM users WHERE username=?", Long.class, u[0]);
      for (String role : u[2].split(",")) jdbc.update("INSERT INTO user_roles(user_id,role) VALUES (?,?) ON CONFLICT DO NOTHING", id, role);
    }
  }
  private void putConfig(String key, Object value) throws Exception {
    jdbc.update("INSERT INTO rules_config(key,value) VALUES (?,?::jsonb) ON CONFLICT(key) DO NOTHING", key, mapper.writeValueAsString(value));
  }
  @FunctionalInterface interface RowMapper { Object[] map(CSVRecord r); }
  private void seedCsv(Path path, String sql, RowMapper rowMapper) throws Exception {
    if (!Files.exists(path)) return;
    try (Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8); CSVParser parser = CSVFormat.DEFAULT.builder().setHeader().setSkipHeaderRecord(true).get().parse(reader)) {
      for (CSVRecord record : parser) jdbc.update(sql, rowMapper.map(record));
    }
  }
  private static String emptyNull(String value) { return value == null || value.isBlank() ? null : value; }
  private static Date date(String value) { return value == null || value.isBlank() ? null : Date.valueOf(value); }
}
