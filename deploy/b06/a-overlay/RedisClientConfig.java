package cn.bugstack.config;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.codec.JsonJacksonCodec;
import org.redisson.config.Config;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
/** Isolated deployment overlay for the pinned A binary; upstream source remains untouched. */
@Configuration
@EnableConfigurationProperties(RedisClientConfigProperties.class)
public class RedisClientConfig {
 @Bean("redissonClient")
 public RedissonClient redissonClient(ConfigurableApplicationContext context,RedisClientConfigProperties p) {
  if(p.getPassword()==null || p.getPassword().trim().isEmpty())
   throw new IllegalStateException("A Redis password required by B06 deployment");
  Config c=new Config();c.setCodec(JsonJacksonCodec.INSTANCE);
  c.useSingleServer().setAddress("redis://"+p.getHost()+":"+p.getPort()).setPassword(p.getPassword())
   .setConnectionPoolSize(p.getPoolSize()).setConnectionMinimumIdleSize(p.getMinIdleSize())
   .setIdleConnectionTimeout(p.getIdleTimeout()).setConnectTimeout(p.getConnectTimeout())
   .setRetryAttempts(p.getRetryAttempts()).setRetryInterval(p.getRetryInterval())
   .setPingConnectionInterval(p.getPingInterval()).setKeepAlive(p.isKeepAlive());
  return Redisson.create(c);
 }
}
