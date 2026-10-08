package cn.zj.zjmarket.infrastructure.product;
import cn.zj.zjmarket.application.product.*;
import cn.zj.zjmarket.infrastructure.config.*;
import cn.zj.zjmarket.infrastructure.integration.rpc.RpcClientFactory;
import cn.zj.zjmarket.infrastructure.integration.mq.MqClientFactory;
import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.mybatis.spring.*;
import javax.sql.DataSource;
import java.util.*;
@Configuration(proxyBeanMethods=false)
@EnableConfigurationProperties(SyncSettings.class)
@ConditionalOnProperty(name="b.sync.enabled",havingValue="true")
public class SyncConfiguration {
 @Bean SyncStore syncStore(DataSource db){try{
  var f=new SqlSessionFactoryBean();f.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.addMapper(SyncMapper.class);c.addMapper(ProductMapper.class);c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);f.setConfiguration(c);
  var session=new SqlSessionTemplate(f.getObject());var tx=new TransactionTemplate(new DataSourceTransactionManager(db));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);
  return new MyBatisSyncStore(session.getMapper(SyncMapper.class),session.getMapper(ProductMapper.class),tx);
 }catch(Exception e){throw new IllegalStateException("Sync persistence unavailable");}}
 @Bean SyncResultReader syncResultReader(SyncStore store,MqSettings mq,SyncSettings sync){
  var keys=new HashMap<String,String>();keys.put(mq.getAKeyId(),mq.getASecret());
  if(!sync.getPreviousAKeys().isBlank())for(String pair:sync.getPreviousAKeys().split(";")){var parts=pair.split("=",2);if(parts.length!=2 || parts[0].isBlank() || parts[1].isBlank() || keys.putIfAbsent(parts[0],parts[1])!=null)throw new IllegalArgumentException("Invalid trusted previous MQ keys");}
  return new SyncResultReader(mq,store,keys);
 }
 @Bean(destroyMethod="close") RocketMqSyncTransport syncTransport(RpcSettings rpc,MqSettings mq,RpcClientFactory rf,MqClientFactory mf,SyncResultReader reader,SyncSettings s,DatabaseSettings db,
  @Value("${b.product.enabled:false}")boolean product,@Value("${b.product.event-producer:}")String producer,@Value("${b.product.event-source:}")String source,@Value("${b.product.event-channel:}")String channel){
  if(!product || !rpc.getClientId().equals(mq.getProducerId()) || !producer.equals(mq.getProducerId()) || !source.equals(mq.getSource()) || !channel.equals(mq.getChannel()) || !rpc.getSource().equals(source) || !rpc.getChannel().equals(channel))throw new IllegalArgumentException("Product/RPC/MQ identity scopes must agree");
  if(mq.getResultConsumerGroup().equals("B_INTEGRATION_RESULTS-dev") || mq.getResultConsumerGroup().contains("PROBE") || Set.of("B_SYNC_RETRY_TEST-dev","B_SYNC_DLQ_READER-dev").contains(mq.getResultConsumerGroup()))throw new IllegalArgumentException("Sync requires dedicated business consumer group");
  if(s.getScanMillis()<100 || s.getQueryMillis()<100 || s.getBatchSize()<1 || s.getBatchSize()>100 || s.getLeaseMillis()<Math.max(mq.getSendTimeoutMillis(),rpc.getTimeoutMillis())+5000 || s.getMaxReconsumeTimes()!=8)throw new IllegalArgumentException("Invalid synchronization limits");
  if(s.isAcceleratedTest() && (!db.getUrl().matches("^jdbc:mysql://[^/]+/zj_market_b02_test(?:\\?.*)?$") || !db.getUsername().equals("zj_market_b02_test_app")))throw new IllegalArgumentException("Accelerated recovery requires isolated B test database");
  return new RocketMqSyncTransport(rpc,mq,rf,mf,reader);
 }
 @Bean ProductSyncService productSyncService(SyncStore store,RocketMqSyncTransport transport,SyncSettings s){return new ProductSyncService(store,transport,s.getLeaseMillis(),s.getQueryMillis(),s.isAcceleratedTest()?2000:60000,s.isAcceleratedTest()?8000:480000);}
 @Bean SyncWorker syncWorker(ProductSyncService service,RocketMqSyncTransport transport,SyncSettings settings){return new SyncWorker(service,transport,settings);}
}
