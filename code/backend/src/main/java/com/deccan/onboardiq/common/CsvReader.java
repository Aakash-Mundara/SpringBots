package com.deccan.onboardiq.common;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Minimal RFC 4180 CSV reader (quoted fields, embedded commas, escaped quotes, CRLF or LF).
 * Dependency-free on purpose: the seeders, the mock extraction provider and the FR-11 batch
 * command all use it, and it is unit-testable without a Spring context.
 */
public final class CsvReader {

    private CsvReader() {
    }

    /** Reads a file with a header row; each record becomes an ordered header→value map. */
    public static List<Map<String, String>> readWithHeader(Path file) throws IOException {
        try (Reader r = Files.newBufferedReader(file, StandardCharsets.UTF_8)) {
            return readWithHeader(r);
        }
    }

    public static List<Map<String, String>> readWithHeader(Reader reader) throws IOException {
        List<List<String>> rows = parse(reader);
        if (rows.isEmpty()) {
            return Collections.emptyList();
        }
        List<String> header = rows.get(0);
        if (!header.isEmpty()) {
            header.set(0, stripBom(header.get(0)));
        }
        List<Map<String, String>> out = new ArrayList<>(rows.size() - 1);
        for (int i = 1; i < rows.size(); i++) {
            List<String> row = rows.get(i);
            if (row.size() == 1 && row.get(0).isEmpty()) {
                continue; // blank line
            }
            if (row.size() != header.size()) {
                throw new IOException("CSV row " + (i + 1) + " has " + row.size()
                        + " columns, header has " + header.size());
            }
            Map<String, String> rec = new LinkedHashMap<>();
            for (int c = 0; c < header.size(); c++) {
                rec.put(header.get(c).trim(), row.get(c));
            }
            out.add(rec);
        }
        return out;
    }

    /** Parses all records, including the header, as raw string lists. */
    public static List<List<String>> parse(Reader in) throws IOException {
        Reader reader = in.markSupported() ? in : new java.io.BufferedReader(in);
        List<List<String>> rows = new ArrayList<>();
        List<String> row = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        boolean fieldStarted = false;
        int ch;
        while ((ch = reader.read()) != -1) {
            char c = (char) ch;
            if (inQuotes) {
                if (c == '"') {
                    reader.mark(1);
                    int next = reader.read();
                    if (next == '"') {
                        field.append('"');
                    } else {
                        inQuotes = false;
                        if (next == -1) {
                            break;
                        }
                        reader.reset();
                    }
                } else {
                    field.append(c);
                }
                continue;
            }
            switch (c) {
                case '"' -> {
                    if (field.length() == 0) {
                        inQuotes = true;
                    } else {
                        field.append(c); // stray quote inside an unquoted field: keep literally
                    }
                    fieldStarted = true;
                }
                case ',' -> {
                    row.add(field.toString());
                    field.setLength(0);
                    fieldStarted = true;
                }
                case '\r' -> {
                    // swallow; LF ends the record
                }
                case '\n' -> {
                    row.add(field.toString());
                    rows.add(row);
                    row = new ArrayList<>();
                    field.setLength(0);
                    fieldStarted = false;
                }
                default -> {
                    field.append(c);
                    fieldStarted = true;
                }
            }
        }
        if (inQuotes) {
            throw new IOException("CSV ends inside a quoted field");
        }
        if (fieldStarted || field.length() > 0 || !row.isEmpty()) {
            row.add(field.toString());
            rows.add(row);
        }
        return rows;
    }

    private static String stripBom(String s) {
        return !s.isEmpty() && s.charAt(0) == '﻿' ? s.substring(1) : s;
    }
}
