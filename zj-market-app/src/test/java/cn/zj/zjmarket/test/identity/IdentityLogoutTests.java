package cn.zj.zjmarket.test.identity;

import cn.zj.zjmarket.domain.identity.adapter.port.*;
import cn.zj.zjmarket.domain.identity.adapter.repository.IIdentityRepository;
import cn.zj.zjmarket.domain.identity.model.valobj.*;
import cn.zj.zjmarket.domain.identity.service.impl.IdentityService;
import cn.zj.zjmarket.types.exception.AuthFailure;
import java.time.Clock;
import java.util.function.Supplier;
import org.junit.jupiter.api.*;
import static org.mockito.Mockito.*;

class IdentityLogoutTests {
    IIdentityRepository store; IAccessTokenPort tokens; IdentityService service;
    final String refresh="A".repeat(43);
    @BeforeEach void setup() {
        store=mock(IIdentityRepository.class); tokens=mock(IAccessTokenPort.class);
        var passwords=mock(IPasswordPort.class);
        when(passwords.encode(anyString())).thenReturn("public-test-hash");
        when(store.transaction(any())).thenAnswer(call -> ((Supplier<?>)call.getArgument(0)).get());
        service=new IdentityService(store,passwords,tokens,Clock.systemUTC(),900,604800);
    }
    @Test void revokesBothDistinctGrantsInOneTransactionInStableOrder() {
        when(tokens.verify("old-jwt")).thenReturn(new AccessTokenClaims("user-old","z-old",1));
        when(store.refresh(anyString())).thenReturn(new RefreshCredential("digest","a-current",false));
        service.logout("old-jwt",refresh);
        var order=inOrder(store); order.verify(store).transaction(any());
        order.verify(store).revoke("a-current"); order.verify(store).revoke("z-old");
        verify(store,times(1)).transaction(any());
    }
    @Test void sameGrantIsRevokedOnceEvenWithRotatedUsedRefresh() {
        when(tokens.verify("jwt")).thenReturn(new AccessTokenClaims("user","grant",1));
        when(store.refresh(anyString())).thenReturn(new RefreshCredential("digest","grant",true));
        service.logout("jwt",refresh); verify(store,times(1)).revoke("grant");
    }
    @Test void expiredAccessStillRevokesCookieGrant() {
        when(tokens.verify("expired")).thenThrow(new AuthFailure(401,"TOKEN_EXPIRED"));
        when(store.refresh(anyString())).thenReturn(new RefreshCredential("digest","current",false));
        service.logout("expired",refresh); verify(store).revoke("current");
    }
    @Test void malformedCookieDoesNotPreventValidAccessRevocation() {
        when(tokens.verify("jwt")).thenReturn(new AccessTokenClaims("user","grant",1));
        service.logout("jwt","invalid-cookie"); verify(store).revoke("grant");
        verify(store,never()).refresh(anyString());
    }
    @Test void absentOrInvalidCredentialsRemainIdempotent() {
        when(tokens.verify("invalid")).thenThrow(new AuthFailure(401,"TOKEN_INVALID"));
        service.logout(null,null); service.logout("invalid","invalid-cookie");
        verify(store,never()).revoke(anyString()); verify(store,never()).transaction(any());
    }
}
