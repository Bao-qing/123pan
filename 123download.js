// ==UserScript==
// @name         123云盘下载辅助
// @namespace    https://github.com/Bao-qing/123pan
// @version      0.2
// @description  123 Cloud Drive Unlimited Flow
// @match        https://www.123pan.com/*
// @match        https://www.123pan.cn/*
// @grant        none
// @author       Qing
// ==/UserScript==

(function () {
    // 重写 XMLHttpRequest
    const originalXHR = window.XMLHttpRequest;

    function newXHR() {
        const realXHR = new originalXHR();

        realXHR.open = function (method, url, async, user, password) {
            this._url = url;  // 记录请求的 URL
            return originalXHR.prototype.open.apply(this, arguments);
        };

        realXHR.setRequestHeader = function (header, value) {
            let headers = {
                "user-agent": "123pan/v2.4.0(Android_7.1.2;Xiaomi)",
                //"loginuuid": generateUUIDHex(),
                "platform": "android",
                "app-version": "61",
                "x-app-version": "2.4.0"
            }
            // 如果header在列表中，则修改
            if (header.toLowerCase() in headers) {
                value = headers[header.toLowerCase()];
            } else {
                console.log('header:', header);
            }

            return originalXHR.prototype.setRequestHeader.apply(this, arguments);
        };

        // 拦截响应内容，修改 DownloadUrl以适应网页端下载
        realXHR.send = function () {
            const xhrInstance = this;
            this.addEventListener('readystatechange', function () {
                let origin_url;
                let new_url_no_redirect;
                let base64data;
                if (xhrInstance.readyState === 4 && xhrInstance.status === 200) {
                    // 解析响应的 JSON
                    let responseText = xhrInstance.responseText;
                    let responseJSON = JSON.parse(responseText);
                    console.log('Original Response:', responseJSON);

                    // 修改 DownloadUrl
                    if (responseJSON.data && responseJSON.data.DownloadUrl) {
                        origin_url = responseJSON.data.DownloadUrl;
                        new_url_no_redirect = origin_url + "&auto_redirect=0";
                        base64data = btoa(new_url_no_redirect);
                        responseJSON.data.DownloadUrl = "https://web-pro2.123952.com/download-v2/?params=" + base64data + "&is_s3=0";
                        console.log('Modified DownloadUrl:', responseJSON.data.DownloadUrl);
                    }

                    // 将修改后的 JSON 转为字符串
                    let modifiedResponseText = JSON.stringify(responseJSON);

                    // 使用 defineProperty 重写 responseText
                    Object.defineProperty(xhrInstance, 'responseText', {
                        get: function () {
                            return modifiedResponseText;
                        }
                    });
                    console.log('Modified Response:', modifiedResponseText);
                }
            });

            return originalXHR.prototype.send.apply(this, arguments);
        };

        return realXHR;
    }

    window.XMLHttpRequest = newXHR;
})();
