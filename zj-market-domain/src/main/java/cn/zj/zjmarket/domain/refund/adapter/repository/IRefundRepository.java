package cn.zj.zjmarket.domain.refund.adapter.repository;
import java.util.List;
import cn.zj.zjmarket.domain.refund.model.Refund.*;
public interface IRefundRepository {
 void discover(int size);
 List<String> due(int size);
 Lease claim(String refundId);
 boolean renew(Lease lease);
 boolean authorize(Lease lease);
 void finish(Lease lease,Fact fact);
 default void finishCheck(Lease lease,Fact fact){throw new UnsupportedOperationException();}
 void defer(Lease lease,boolean conflict);
 Request noticeRequest(Notice notice);
 boolean applied(Fact fact);
 void quarantineNotice(Notice notice);
}
