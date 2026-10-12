package cn.zj.zjmarket.test.identity;

import cn.zj.zjmarket.app.security.IdentityHttpFilter;
import cn.zj.zjmarket.infrastructure.config.properties.IdentitySettings;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.servlet.HandlerMapping;
import static org.junit.jupiter.api.Assertions.*;

class RequestObservationTests {
    @Test void logsOnlyRouteTemplateAndGeneratedIdEvenWithHostileInput() throws Exception {
        Logger logger=(Logger)LoggerFactory.getLogger("b.observability.http");
        var logs=new ListAppender<ILoggingEvent>();logs.start();logger.addAppender(logs);
        try {
            var settings=new IdentitySettings();settings.setEnabled(false);
            var filter=new IdentityHttpFilter(settings,null,null,true);
            var req=new MockHttpServletRequest("GET","/api/v1/orders/DO_NOT_LOG_PATH");
            req.setQueryString("token=DO_NOT_LOG_QUERY");req.addHeader("Authorization","Bearer DO_NOT_LOG_HEADER");
            req.setContent("DO_NOT_LOG_BODY".getBytes());var res=new MockHttpServletResponse();
            filter.doFilter(req,res,(request,response)->{
                assertEquals(res.getHeader("X-Request-Id"),MDC.get("requestId"));
                request.setAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE,"/api/v1/orders/{orderId}");
                ((jakarta.servlet.http.HttpServletResponse)response).setStatus(404);
            });
            assertNull(MDC.get("requestId"));assertEquals(1,logs.list.size());
            var values=logs.list.getFirst().getKeyValuePairs().stream().collect(java.util.stream.Collectors.toMap(k->k.key,k->k.value));
            String fields=values.toString();
            assertEquals(404,values.get("status"));assertTrue(fields.contains("/api/v1/orders/{orderId}"));
            assertTrue(fields.contains(res.getHeader("X-Request-Id")));assertFalse(fields.contains("DO_NOT_LOG"));
        } finally {logger.detachAppender(logs);logs.stop();MDC.remove("requestId");}
    }
    @Test void uncaughtFailureLogs500AndDoesNotLeaveMdc() {
        Logger logger=(Logger)LoggerFactory.getLogger("b.observability.http");
        var logs=new ListAppender<ILoggingEvent>();logs.start();logger.addAppender(logs);
        try {
            var settings=new IdentitySettings();settings.setEnabled(false);
            var filter=new IdentityHttpFilter(settings,null,null,true);
            assertThrows(jakarta.servlet.ServletException.class,()->filter.doFilter(new MockHttpServletRequest("POST","/api/unknown/private"),new MockHttpServletResponse(),(req,res)->{throw new jakarta.servlet.ServletException("DO_NOT_LOG_EXCEPTION");}));
            assertNull(MDC.get("requestId"));assertEquals(1,logs.list.size());
            var values=logs.list.getFirst().getKeyValuePairs().stream().collect(java.util.stream.Collectors.toMap(k->k.key,k->k.value));
            String fields=values.toString();
            assertEquals(500,values.get("status"));assertTrue(fields.contains("UNMAPPED"));assertFalse(fields.contains("DO_NOT_LOG"));
        } finally {logger.detachAppender(logs);logs.stop();MDC.remove("requestId");}
    }
}
