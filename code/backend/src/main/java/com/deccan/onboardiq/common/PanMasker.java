package com.deccan.onboardiq.common;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * PAN masking (Section 6.7): first 3 characters + "XXXXX" + last 2, e.g. ZZKPS1234Q → ZZKXXXXX4Q.
 * {@link #maskAll(String)} masks every PAN-shaped token inside free text (used by the Logback
 * converter added in a later phase, and by exports).
 */
public final class PanMasker {

    /** 5 letters + 4 digits + 1 letter, as a whole token. */
    private static final Pattern PAN_TOKEN = Pattern.compile("\\b([A-Z]{3})[A-Z]{2}[0-9]{3}([0-9][A-Z])\\b");

    private PanMasker() {
    }

    public static String mask(String pan) {
        if (pan == null) {
            return null;
        }
        String p = pan.trim();
        if (p.length() < 5) {
            return "XXXXX";
        }
        return p.substring(0, 3) + "XXXXX" + p.substring(p.length() - 2);
    }

    public static String maskAll(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }
        Matcher m = PAN_TOKEN.matcher(text);
        return m.replaceAll("$1XXXXX$2");
    }
}
