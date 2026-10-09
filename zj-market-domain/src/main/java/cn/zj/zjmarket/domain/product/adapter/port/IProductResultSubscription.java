package cn.zj.zjmarket.domain.product.adapter.port;

/** Subscription lifecycle is implemented by the message adapter, without exposing SDK types. */
public interface IProductResultSubscription { void startConsumer(int retries,boolean accelerated) throws Exception; }
