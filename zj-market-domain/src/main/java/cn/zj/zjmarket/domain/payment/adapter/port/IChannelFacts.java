package cn.zj.zjmarket.domain.payment.adapter.port;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
import java.util.List;
public interface IChannelFacts {
 ChannelFact fact(String payment,String attempt);
 List<ChannelNotice> notices(int size);
 void retry(ChannelNotice notice);
 void acknowledge(ChannelNotice notice,boolean review);
}
