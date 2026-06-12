
// site.js - WhatsApp 点击转化已集成

// 原有网站统计逻辑保持
(function(){
    // 你的原有 GA4 或其他事件逻辑可以继续放这里
})();

// Google Ads WhatsApp 点击事件
document.addEventListener('DOMContentLoaded', function() {
    const whatsappBtns = document.querySelectorAll('.btn-whatsapp'); // 你仓库的按钮 class
    whatsappBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            // 调用官方事件包装函数，保证跳转统计完成
            var callback = function () {
                // 保持默认 WhatsApp 跳转
                const href = btn.getAttribute('href');
                if (typeof href !== 'undefined') {
                    window.location = href;
                }
            };
            gtag('event', 'conversion', {
                'send_to': 'AW-18109380838/Jk3_CKzmx70cEObxnLtD',
                'event_callback': callback
            });
        });
    });
});
