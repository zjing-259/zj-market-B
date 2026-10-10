package cn.zj.zjmarket.domain.payment.adapter.port;
import cn.zj.zjmarket.domain.payment.model.valobj.*;
public interface IChannelClosing {
 ChannelClosure queryClose(PaymentClose request);
 ChannelClosure closeRoot(PaymentClose request);
}
