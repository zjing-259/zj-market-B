package cn.zj.zjmarket.app.config;
import cn.zj.zjmarket.domain.payment.adapter.repository.*;
import cn.zj.zjmarket.domain.payment.adapter.port.*;
import cn.zj.zjmarket.domain.payment.service.*;
import cn.zj.zjmarket.domain.payment.service.impl.SettlementService;
import cn.zj.zjmarket.domain.order.adapter.repository.IOrderRepository;
import cn.zj.zjmarket.infrastructure.adapter.repository.SettlementRepository;
import cn.zj.zjmarket.infrastructure.adapter.port.payment.*;
import cn.zj.zjmarket.infrastructure.config.properties.*;
import cn.zj.zjmarket.infrastructure.gateway.mq.*;
import cn.zj.zjmarket.infrastructure.gateway.rpc.RpcClientFactory;
import cn.zj.zjmarket.trigger.job.SettlementJob;
import javax.sql.DataSource;
import java.util.*;
import org.springframework.context.annotation.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
@Configuration(proxyBeanMethods=false)
@ConditionalOnProperty(name="b.trade.events-enabled",havingValue="true")
public class SettlementConfiguration {
 @Bean ISettlementRepository settlementRepository(DataSource ds,IOrderRepository orders,MqSettings mq,IPaymentService payments){var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return new SettlementRepository(ds,tx,orders,mq.getProducerId(),mq.getSource(),mq.getChannel());}
 @Bean org.springframework.beans.factory.InitializingBean paymentClosing(DataSource ds,IOrderRepository orders,ISimulatedChannel simulator,ISettlementRepository settlement,cn.zj.zjmarket.infrastructure.adapter.repository.TradeRepository trade){var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return ()->trade.enablePaymentClosing(new cn.zj.zjmarket.infrastructure.adapter.repository.PaymentClosingRepository(ds,tx,orders,(IChannelClosing)simulator,settlement));}
 @Bean IFulfillmentRepository fulfillmentRepository(DataSource ds,IOrderRepository orders,ISettlementRepository settlement){var tx=new TransactionTemplate(new DataSourceTransactionManager(ds));tx.setIsolationLevel(org.springframework.transaction.TransactionDefinition.ISOLATION_READ_COMMITTED);tx.setTimeout(15);return new cn.zj.zjmarket.infrastructure.adapter.repository.FulfillmentRepository(ds,tx,orders,settlement);}
 @Bean cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService fulfillmentService(IFulfillmentRepository repo,RocketMqSettlementTransport transport){return new cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService(repo,transport);}
 @Bean TradeMessageReader tradeMessageReader(MqSettings mq,ISettlementRepository repo,@Value("${b.sync.previous-a-keys:}")String previous){var keys=new HashMap<String,String>();keys.put(mq.getAKeyId(),mq.getASecret());if(!previous.isBlank())for(String pair:previous.split(";")){var p=pair.split("=",2);if(p.length!=2||p[0].isBlank()||p[1].isBlank()||keys.putIfAbsent(p[0],p[1])!=null)throw new IllegalArgumentException("Invalid previous A keys");}return new TradeMessageReader(mq,repo,keys);}
 @Bean(destroyMethod="close") RocketMqSettlementTransport settlementTransport(RpcSettings rpc,MqSettings mq,RpcClientFactory rf,MqClientFactory mf,TradeMessageReader reader,IOrderRepository orders,@Value("${b.trade.event-topic:}")String topic,@Value("${b.trade.result-group:}")String result,@Value("${b.trade.team-group:}")String team){
  if(!mq.isEnabled()||!rpc.isEnabled()||topic.isBlank()||result.isBlank()||team.isBlank()||result.equals(team)||result.equals(mq.getResultConsumerGroup())||team.equals(mq.getResultConsumerGroup())||result.contains("PROBE")||team.contains("PROBE")||!rpc.getClientId().equals(mq.getProducerId())||!rpc.getSource().equals(mq.getSource())||!rpc.getChannel().equals(mq.getChannel()))throw new IllegalArgumentException("Trade events require independent groups and matching RPC/MQ scopes");
  return new RocketMqSettlementTransport(rpc,mq,rf,mf,reader,orders,topic,result,team);}
 @Bean ISettlementService settlementService(ISettlementRepository repo,ISimulatedChannel simulator,RocketMqSettlementTransport transport){return new SettlementService(repo,(IChannelFacts)simulator,transport);}
 @Bean SettlementJob settlementJob(ISettlementService service,RocketMqSettlementTransport transport,cn.zj.zjmarket.domain.payment.service.impl.FulfillmentService fulfillment,@Value("${b.trade.events-scheduler-enabled:true}")boolean enabled){var job=new SettlementJob(service,transport,enabled);job.enableFulfillment(fulfillment);return job;}
}
