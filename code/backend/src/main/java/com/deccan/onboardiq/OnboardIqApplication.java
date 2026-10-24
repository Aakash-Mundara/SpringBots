package com.deccan.onboardiq;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

import java.util.TimeZone;

@SpringBootApplication
@ConfigurationPropertiesScan
public class OnboardIqApplication {

    public static void main(String[] args) {
        // All business dates are calendar dates in IST (NFR "Precision").
        TimeZone.setDefault(TimeZone.getTimeZone(System.getenv().getOrDefault("APP_TIMEZONE", "Asia/Kolkata")));
        SpringApplication.run(OnboardIqApplication.class, args);
    }
}
