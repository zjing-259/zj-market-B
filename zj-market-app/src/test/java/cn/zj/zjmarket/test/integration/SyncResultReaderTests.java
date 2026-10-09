package cn.zj.zjmarket.test.integration;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.model.valobj.*;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader;
import cn.zj.zjmarket.types.exception.SyncTransportFailure;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class SyncResultReaderTests {
    static final String SECRET="public-reader-fixture-secret";
    static final String VALID="""
        {"eventId":"receipt-1","eventType":"EVENT_PROCESSING_RESULT","schemaVersion":1,
         "producer":"group-buy-market","occurredAt":"2026-10-09T00:00:00.000Z",
         "source":"s01","channel":"c01","correlationId":"event-1",
         "payload":{"originalEventId":"event-1","originalEventType":"PRODUCT_SNAPSHOT_CHANGED",
          "outcome":"APPLIED","code":"0000","info":"ok","processedAt":"2026-10-09T00:00:00.000Z",
          "result":{"goodsId":"goods-1","currentVersion":"1","applied":true,"saleStatus":"ON_SALE"}}}
        """;
    MqSettings mq; IProductSyncRepository store; SyncResultReader reader;
    @BeforeEach void setup() {
        mq=new MqSettings(); mq.setResultTopic("A_INTEGRATION_RESULTS-dev");
        mq.setSource("s01"); mq.setChannel("c01");
        store=mock(IProductSyncRepository.class);
        reader=new SyncResultReader(mq,store,Map.of("fixture-key",SECRET));
    }
    SyncBadMessage signed(String raw)throws Exception {
        byte[] bytes=raw.getBytes(StandardCharsets.UTF_8);
        return new SyncBadMessage(mq.getResultTopic(),"EVENT_PROCESSING_RESULT","fixture-key",
                ContractCodec.hmac(SECRET,mq.getResultTopic()+"\n"+ContractCodec.sha256(bytes)),bytes,null);
    }
    @Test void acceptsExactlyOneSignedDocumentIncludingTrailingWhitespace()throws Exception {
        assertEquals("1",reader.decode(signed(VALID)).currentVersion());
        assertEquals("1",reader.decode(signed(VALID+" \r\n\t")).currentVersion());
    }
    @Test void rejectsSignedTrailingObjectsArraysScalarsAndGarbage()throws Exception {
        for(String tail:new String[]{"{}","[]","true","1","null","garbage"}) {
            var bad=signed(VALID+tail);
            assertEquals("RESULT_STRUCTURE_INVALID",assertThrows(SyncTransportFailure.class,()->reader.decode(bad)).code(),tail);
        }
    }
    @Test void rejectsVersionsWithoutIntegerTruncationOrCoercion()throws Exception {
        for(String version:new String[]{"4294967297","-4294967295","18446744073709551617","2","0","-1","1.0","\"1\"","null","true"}) {
            var bad=signed(VALID.replace("\"schemaVersion\":1","\"schemaVersion\":"+version));
            assertEquals("SCHEMA_INVALID",assertThrows(SyncTransportFailure.class,()->reader.decode(bad)).code(),version);
        }
    }
    @Test void validatesSignatureBeforeParsingMalformedBody()throws Exception {
        var validSignature=signed("not-json");
        var bad=new SyncBadMessage(validSignature.topic(),validSignature.tag(),validSignature.keyId(),"invalid",validSignature.body(),null);
        assertEquals("SIGNATURE_INVALID",assertThrows(SyncTransportFailure.class,()->reader.decode(bad)).code());
    }
    @Test void persistsMalformedMessageInQuarantineWithoutApplyingResult()throws Exception {
        var bad=signed(VALID+"{}"); assertFalse(reader.receive(bad));
        verify(store,never()).accept(any(),anyString());
        var captured=org.mockito.ArgumentCaptor.forClass(SyncBadMessage.class);verify(store).quarantine(captured.capture());
        assertArrayEquals(bad.body(),captured.getValue().body());
        assertEquals("RESULT_STRUCTURE_INVALID",captured.getValue().reason());
    }
    @Test void quarantinePersistenceFailurePropagatesForBrokerRetry()throws Exception {
        doThrow(new IllegalStateException("controlled persistence failure")).when(store).quarantine(any());
        var bad=signed(VALID+"{}"); assertThrows(IllegalStateException.class,()->reader.receive(bad));
        verify(store,never()).accept(any(),anyString());
    }
}
