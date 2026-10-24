package com.deccan.onboardiq.common;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.time.ZoneId;

/**
 * Single injectable clock in IST. Business code asks for {@code LocalDate.now(clock)} instead of
 * {@code LocalDate.now()} so that tests can pin the date (e.g. the 29-Feb re-KYC case).
 */
@Configuration
public class ClockConfig {

    @Bean
    public Clock clock(@Value("${onboardiq.timezone:Asia/Kolkata}") String zone) {
        return Clock.system(ZoneId.of(zone));
    }
}
