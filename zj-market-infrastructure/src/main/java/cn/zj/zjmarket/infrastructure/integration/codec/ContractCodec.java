package cn.zj.zjmarket.infrastructure.integration.codec;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.MapperFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.HexFormat;

/** A's Jackson 2 canonical wire format; independent of B's HTTP Jackson 3 mapper. */
public final class ContractCodec {
    private final ObjectMapper mapper = new ObjectMapper()
            .configure(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
            .setSerializationInclusion(JsonInclude.Include.ALWAYS);

    public byte[] encode(Object value) throws Exception { return mapper.writeValueAsBytes(value); }
    public <T> T decode(byte[] body, Class<T> type) throws Exception { return mapper.readValue(body, type); }
    public static String sha256(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }
    public static String hmac(String secret, String text) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return Base64.getEncoder().encodeToString(mac.doFinal(text.getBytes(StandardCharsets.UTF_8)));
    }
    public static boolean validSignature(String secret, String topic, byte[] body, String signature) throws Exception {
        return signature != null && MessageDigest.isEqual(
                hmac(secret, topic + "\n" + sha256(body)).getBytes(StandardCharsets.US_ASCII),
                signature.getBytes(StandardCharsets.US_ASCII));
    }
}
