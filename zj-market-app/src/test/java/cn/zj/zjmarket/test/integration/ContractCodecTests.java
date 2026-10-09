package cn.zj.zjmarket.test.integration;

import cn.bugstack.api.v2.TrialRequest;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class ContractCodecTests {
    @Test void matchesPublishedASigningVectorIncludingUnicodeAndNull() throws Exception {
        TrialRequest request = new TrialRequest();
        request.setSource("s01"); request.setChannel("c01"); request.setUserId("用户A");
        request.setGoodsId("sku-1"); request.setProductVersion("2"); request.setQuantity(1);
        byte[] body = new ContractCodec().encode(request);
        assertEquals("{\"activityId\":null,\"channel\":\"c01\",\"goodsId\":\"sku-1\",\"productVersion\":\"2\",\"quantity\":1,\"source\":\"s01\",\"userId\":\"用户A\"}",
                new String(body, StandardCharsets.UTF_8));
        String hash = ContractCodec.sha256(body);
        assertEquals("16ee67b9b6441df3bf88995fea03003e5d81f82707bf3f8be9826868d7e6c21d", hash);
        String text = String.join("\n", "zj-market", "test-key-1", "1790932800000",
                "AAAAAAAAAAAAAAAAAAAAAA", "req-001", "cn.bugstack.api.v2.MarketingService",
                "trial", "2.0.0", "gbm-dev", hash);
        assertEquals("uIBO9F14kK798WO51+IOE7RP2wrz3rvuRzwGVzpJnwc=", ContractCodec.hmac("test-secret-123", text));
    }

    @Test void signedMqBodyCannotBeReusedOnAnotherTopicOrChanged() throws Exception {
        byte[] body = "{}".getBytes(StandardCharsets.UTF_8);
        String signature = ContractCodec.hmac("public-test-key", "A_INTEGRATION_RESULTS-dev\n" + ContractCodec.sha256(body));
        assertTrue(ContractCodec.validSignature("public-test-key", "A_INTEGRATION_RESULTS-dev", body, signature));
        assertFalse(ContractCodec.validSignature("public-test-key", "A_TEAM_EVENTS-dev", body, signature));
        assertFalse(ContractCodec.validSignature("public-test-key", "A_INTEGRATION_RESULTS-dev", "{ }".getBytes(StandardCharsets.UTF_8), signature));
    }
}
