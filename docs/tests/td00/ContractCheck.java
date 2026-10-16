import cn.bugstack.api.v2.*;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.*;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
import java.util.jar.*;

/** Runs on Java 8 and Java 21 against the same frozen Java 8 transport artifact. */
public final class ContractCheck {
    public static void main(String[] args) throws Exception {
        ObjectMapper json = new ObjectMapper().configure(MapperFeature.SORT_PROPERTIES_ALPHABETICALLY, true)
            .configure(SerializationFeature.ORDER_MAP_ENTRIES_BY_KEYS, true)
            .setSerializationInclusion(JsonInclude.Include.ALWAYS);
        JsonNode vectors = json.readTree(Paths.get(args[2]).toFile());
        TeamDiscoveryRequest request = json.treeToValue(vectors.get("request"), TeamDiscoveryRequest.class);
        require(json.writeValueAsString(request).equals(vectors.get("canonicalRequestJson").asText()), "request signing bytes");
        TeamDiscoveryPage page = json.treeToValue(vectors.get("page"), TeamDiscoveryPage.class);
        require(page.getItems().size() == 1 && page.getItems().get(0).getPaidCount() == 1, "typed nested item");
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ObjectOutputStream out = new ObjectOutputStream(bytes)) { out.writeObject(page); }
        try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(bytes.toByteArray()))) {
            require(json.writeValueAsString(in.readObject()).equals(json.writeValueAsString(page)), "Java serialization round trip");
        }
        Method list = TeamDiscoveryService.class.getMethod("list", TeamDiscoveryRequest.class);
        require(list.getGenericReturnType().getTypeName().equals("cn.bugstack.api.v2.RpcResult<cn.bugstack.api.v2.TeamDiscoveryPage>"), "RPC signature");
        int compared = 0;
        try (URLClassLoader old = new URLClassLoader(new URL[]{Paths.get(args[0]).toUri().toURL()}, null);
             URLClassLoader fresh = new URLClassLoader(new URL[]{Paths.get(args[1]).toUri().toURL()}, null);
             JarFile jar = new JarFile(args[0])) {
            Enumeration<JarEntry> entries = jar.entries();
            while (entries.hasMoreElements()) {
                String name = entries.nextElement().getName();
                if (!name.endsWith(".class")) continue;
                String type = name.substring(0, name.length()-6).replace('/', '.');
                Class<?> before = old.loadClass(type), after = fresh.loadClass(type);
                require(before.getModifiers()==after.getModifiers(), type+" modifiers");
                require(Objects.equals(supertype(before), supertype(after)), type+" superclass");
                for (Field f : before.getDeclaredFields()) {
                    Field n = after.getDeclaredField(f.getName());
                    require(f.getGenericType().getTypeName().equals(n.getGenericType().getTypeName()) && f.getModifiers()==n.getModifiers(), type+" field "+f.getName());
                    if (Modifier.isStatic(f.getModifiers()) && Modifier.isFinal(f.getModifiers())) {
                        f.setAccessible(true); n.setAccessible(true);
                        require(Objects.equals(f.get(null),n.get(null)), type+" constant "+f.getName());
                    }
                }
                for (Method m : before.getDeclaredMethods()) {
                    boolean found = false;
                    for (Method n : after.getDeclaredMethods()) if (m.toGenericString().equals(n.toGenericString())) found=true;
                    require(found, type+" method "+m.getName());
                }
                if (!type.endsWith(".V2Codes")) require(before.getDeclaredFields().length==after.getDeclaredFields().length && before.getDeclaredMethods().length==after.getDeclaredMethods().length, type+" unchanged shape");
                compared++;
            }
        }
        System.out.println("PASS legacy types="+compared+"; canonical JSON, RPC signature, nested DTO and serialization; Java="+System.getProperty("java.version"));
    }
    static String supertype(Class<?> c) { return c.getSuperclass()==null?null:c.getSuperclass().getName(); }
    static void require(boolean yes, String message) { if (!yes) throw new AssertionError(message); }
}
