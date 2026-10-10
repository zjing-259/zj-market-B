package cn.zj.zjmarket.test.inventory;
import cn.zj.zjmarket.domain.inventory.model.entity.InventoryAccount;
import cn.zj.zjmarket.types.exception.InventoryFailure;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class InventoryAccountTest {
 @Test void reservationLifecycleConservesStock(){var a=new InventoryAccount("sku",3,0,0,1,0);var held=a.reserve(1,1);var sold=held.confirm(1,2);assertEquals(2,sold.available());assertEquals(0,sold.reserved());assertEquals(1,sold.sold());var released=held.release(1,2);assertEquals(3,released.available());assertEquals(0,released.reserved());}
 @Test void adjustmentCannotInvadeHeldStock(){var a=new InventoryAccount("sku",2,5,7,1,0);assertThrows(InventoryFailure.class,()->a.adjust(-3,1));var b=a.adjust(-2,1);assertEquals(0,b.available());assertEquals(5,b.reserved());assertEquals(7,b.sold());}
 @Test void quantityAndVersionOverflowNeverWrap(){assertThrows(ArithmeticException.class,()->new InventoryAccount("sku",Long.MAX_VALUE,0,0,1,0).adjust(1,1));assertThrows(ArithmeticException.class,()->new InventoryAccount("sku",1,0,0,Long.MAX_VALUE,0).adjust(1,1));}
 @Test void invalidResolutionCannotProduceNegativeReserved(){var a=new InventoryAccount("sku",0,0,0,1,0);assertThrows(IllegalArgumentException.class,()->a.release(1,1));assertThrows(IllegalArgumentException.class,()->a.confirm(1,1));assertThrows(IllegalArgumentException.class,()->a.reserve(0,1));}
}
