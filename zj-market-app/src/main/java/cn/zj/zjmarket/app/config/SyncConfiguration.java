package cn.zj.zjmarket.app.config;

import cn.zj.zjmarket.domain.product.adapter.repository.IProductSyncRepository;
import cn.zj.zjmarket.domain.product.service.IProductSyncService;
import cn.zj.zjmarket.domain.product.service.impl.ProductSyncService;
import cn.zj.zjmarket.infrastructure.adapter.port.product.RocketMqSyncTransport;
import cn.zj.zjmarket.infrastructure.adapter.repository.ProductSyncRepository;
import cn.zj.zjmarket.infrastructure.config.properties.DatabaseSettings;
import cn.zj.zjmarket.infrastructure.config.properties.MqSettings;
import cn.zj.zjmarket.infrastructure.config.properties.RpcSettings;
import cn.zj.zjmarket.infrastructure.config.properties.SyncSettings;
import cn.zj.zjmarket.infrastructure.dao.IProductDao;
import cn.zj.zjmarket.infrastructure.dao.IProductSyncDao;
import cn.zj.zjmarket.infrastructure.gateway.mq.MqClientFactory;
import cn.zj.zjmarket.infrastructure.gateway.mq.SyncResultReader;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.trigger.job.ProductSyncJob;
import java.util.*;
import javax.sql.DataSource;
import org.mybatis.spring.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.*;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@EnableConfigurationProperties(SyncSettings.class)
@ConditionalOnProperty(name="b.sync.enabled",havingValue="true")
public class SyncConfiguration {
 @Bean IProductSyncRepository syncStore(DataSource db){try{
  var f=new SqlSessionFactoryBean();f.setDataSource(db);var c=new org.apache.ibatis.session.Configuration();c.addMapper(IProductSyncDao.class);c.addMapper(IProductDao.class);c.setLocalCacheScope(org.apache.ibatis.session.LocalCacheScope.STATEMENT);f.setConfiguration(c);
  var session=new SqlSessionTemplate(f.getObject());var tx=new TransactionTemplate(new DataSourceTransactionManager(db));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);
  return new ProductSyncRepository(session.getMapper(IProductSyncDao.class),session.getMapper(IProductDao.class),tx);
 }catch(Exception e){throw new IllegalStateException("Sync persistence unavailable");}}
 @Bean SyncResultReader syncResultReader(IProductSyncRepository store,MqSettings mq,SyncSettings sync){
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
 @Bean IProductSyncService productSyncService(IProductSyncRepository store,RocketMqSyncTransport transport,SyncSettings s){return new ProductSyncService(store,transport,s.getLeaseMillis(),s.getQueryMillis(),s.isAcceleratedTest()?2000:60000,s.isAcceleratedTest()?8000:480000);}
 @Bean ProductSyncJob syncWorker(IProductSyncService service,RocketMqSyncTransport transport,SyncSettings settings){return new ProductSyncJob(service,transport,settings.getScanMillis(),settings.getBatchSize(),settings.isSchedulerEnabled(),settings.getMaxReconsumeTimes(),settings.isAcceleratedTest());}
}
