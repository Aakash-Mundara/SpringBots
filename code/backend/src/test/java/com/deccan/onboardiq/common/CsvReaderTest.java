package com.deccan.onboardiq.common;

import org.junit.jupiter.api.Test;

import java.io.StringReader;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class CsvReaderTest {

    @Test
    void parsesQuotedFieldsWithCommasAndEscapedQuotes() throws Exception {
        String csv = "a,b,c\r\n1,\"x, y\",\"he said \"\"hi\"\"\"\r\n2,,last\n";
        List<Map<String, String>> rows = CsvReader.readWithHeader(new StringReader(csv));
        assertThat(rows).hasSize(2);
        assertThat(rows.get(0)).containsEntry("b", "x, y").containsEntry("c", "he said \"hi\"");
        assertThat(rows.get(1)).containsEntry("b", "").containsEntry("c", "last");
    }

    @Test
    void handlesMissingTrailingNewlineAndTrailingEmptyField() throws Exception {
        List<Map<String, String>> rows = CsvReader.readWithHeader(new StringReader("a,b\n1,"));
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0)).containsEntry("a", "1").containsEntry("b", "");
    }

    @Test
    void rejectsRaggedRows() {
        assertThatThrownBy(() -> CsvReader.readWithHeader(new StringReader("a,b\n1,2,3\n")))
                .hasMessageContaining("3 columns");
    }

    @Test
    void readsEveryDataPackFile() throws Exception {
        Path data = Path.of("../../data");
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_occupations_V1.0.csv"))).hasSize(12);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_sanctions_list_V1.0.csv"))).hasSize(50);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_pep_list_V1.0.csv"))).hasSize(60);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_existing_customers_V1.0.csv"))).hasSize(300);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_applications_sample_V1.0.csv"))).hasSize(60);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_applications_eval_V1.0.csv"))).hasSize(100);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_documents_sample_V1.0.csv"))).hasSize(178);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_documents_eval_V1.0.csv"))).hasSize(296);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_extraction_mock_sample_V1.0.csv"))).hasSize(946);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_extraction_mock_eval_V1.0.csv"))).hasSize(1583);
        assertThat(CsvReader.readWithHeader(data.resolve("case_02_document_truth_sample_V1.0.csv"))).hasSize(178);

        Map<String, String> a1 = CsvReader.readWithHeader(data.resolve("case_02_applications_sample_V1.0.csv")).get(0);
        assertThat(a1.get("address")).isEqualTo("Flat 12, Lotus Residency, MG Road, Mumbai, Maharashtra");
    }
}
