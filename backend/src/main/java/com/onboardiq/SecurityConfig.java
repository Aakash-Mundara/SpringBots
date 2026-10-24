package com.onboardiq;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {
  @Bean BCryptPasswordEncoder passwordEncoder() { return new BCryptPasswordEncoder(); }
  @Bean SecurityFilterChain phaseOneSecurity(HttpSecurity http) throws Exception {
    // Phase 1 exposes only health/docs. Role-based JWT security is implemented in Phase 3.
    http.csrf(csrf -> csrf.disable()).authorizeHttpRequests(auth -> auth
      .requestMatchers("/api/v1/health", "/actuator/health", "/swagger-ui.html", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
      .anyRequest().authenticated()).httpBasic(Customizer.withDefaults());
    return http.build();
  }
}
