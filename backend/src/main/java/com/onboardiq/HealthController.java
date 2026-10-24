package com.onboardiq;

import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/v1/health")
  public Map<String, Object> health() {
    return Map.of("status", "UP", "service", "onboardiq", "time", OffsetDateTime.now(ZoneId.of("Asia/Kolkata")), "phase", 1);
  }
}
