package cn.zj.zjmarket.infrastructure.adapter.port.product;

import cn.bugstack.api.v2.*;
import cn.zj.zjmarket.domain.product.adapter.port.IProductEventPort;
import cn.zj.zjmarket.domain.product.model.entity.Product;
import cn.zj.zjmarket.infrastructure.gateway.codec.ContractCodec;
import cn.zj.zjmarket.types.exception.ProductFailure;
import java.nio.charset.StandardCharsets;
import java.time.*;
import java.time.format.DateTimeFormatter;
/** Saves exact A contract bytes at business commit; signing/delivery belong to B-02.4. */
public final class ContractProductEvents implements IProductEventPort {
    private final String producer,source,channel;private final ContractCodec codec=new ContractCodec();
    public ContractProductEvents(String producer,String source,String channel){
        if(!id(producer,64) || !id(source,8) || !id(channel,8))throw new IllegalArgumentException("Explicit product event producer/source/channel required");
        this.producer=producer;this.source=source;this.channel=channel;
    }
    private static boolean id(String value,int max){return value!=null && value.matches("[A-Za-z0-9._-]{1,"+max+"}");}
    public String encode(Product p,String eventId,String correlationId){
        var f=p.fields();var payload=new ProductSnapshotChanged();payload.setGoodsId(p.goodsId());payload.setProductVersion(Long.toString(p.version()));payload.setGoodsName(f.goodsName());payload.setOriginalPrice(f.originalPrice().toPlainString());payload.setCurrency(f.currency());payload.setSaleStatus(f.saleStatus().name());
        var envelope=new EventEnvelope();envelope.setEventId(eventId);envelope.setEventType("PRODUCT_SNAPSHOT_CHANGED");envelope.setSchemaVersion(1);envelope.setProducer(producer);
        envelope.setOccurredAt(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC).format(Instant.ofEpochMilli(p.updatedAt())));
        envelope.setSource(source);envelope.setChannel(channel);envelope.setCorrelationId(correlationId);envelope.setPayload(payload);
        try{byte[] bytes=codec.encode(envelope);if(bytes.length>256*1024)throw new IllegalArgumentException("Event body exceeds contract limit");return new String(bytes,StandardCharsets.UTF_8);}
        catch(Exception e){throw new ProductFailure(503,"DEPENDENCY_UNAVAILABLE");}
    }
}
