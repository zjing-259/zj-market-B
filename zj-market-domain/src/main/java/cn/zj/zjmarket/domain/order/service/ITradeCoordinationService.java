package cn.zj.zjmarket.domain.order.service;
public interface ITradeCoordinationService { int tick(int batch); void recover(String orderId); }
