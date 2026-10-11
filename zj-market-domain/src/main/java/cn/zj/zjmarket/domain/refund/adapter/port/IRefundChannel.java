package cn.zj.zjmarket.domain.refund.adapter.port;
import java.util.List;
import cn.zj.zjmarket.domain.refund.model.Refund.*;
public interface IRefundChannel {
 Fact execute(Request request);
 Fact query(Request request);
 List<Notice> notices(int size);
 boolean renew(Notice notice);
 void acknowledge(Notice notice,boolean review);
 void retry(Notice notice);
}
