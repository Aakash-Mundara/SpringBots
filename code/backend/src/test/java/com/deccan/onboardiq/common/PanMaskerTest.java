package com.deccan.onboardiq.common;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class PanMaskerTest {

    @Test
    void masksAsSpecified() {
        assertThat(PanMasker.mask("ZZKPS1234Q")).isEqualTo("ZZKXXXXX4Q");
    }

    @Test
    void masksEveryPanInsideFreeText() {
        assertThat(PanMasker.maskAll("declared ZZKPS1234Q vs card ZZMPN3465S."))
                .isEqualTo("declared ZZKXXXXX4Q vs card ZZMXXXXX5S.");
    }

    @Test
    void leavesNonPanTokensAlone() {
        assertThat(PanMasker.maskAll("A2000001 D3000001 400001")).isEqualTo("A2000001 D3000001 400001");
    }
}
