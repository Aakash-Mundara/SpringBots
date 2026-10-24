package com.onboardiq;

import io.awspring.cloud.s3.S3Template;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.S3Exception;

@Configuration
@Profile("local")
public class S3BucketBootstrap {
  @Bean ApplicationRunner ensureDocumentBucket(S3Client s3, @Value("${app.s3.bucket:onboardiq-docs}") String bucket) {
    return args -> {
      try { s3.headBucket(HeadBucketRequest.builder().bucket(bucket).build()); }
      catch (S3Exception e) {
        if (e.statusCode() == 404 || e.statusCode() == 403 || "NoSuchBucket".equals(e.awsErrorDetails() == null ? null : e.awsErrorDetails().errorCode())) {
          s3.createBucket(CreateBucketRequest.builder().bucket(bucket).build());
        } else throw e;
      }
    };
  }
}
