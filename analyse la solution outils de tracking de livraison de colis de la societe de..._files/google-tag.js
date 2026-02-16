// Google tag (gtag.js)
(function (w, d, s, l, i) {
  w[l] = w[l] || [];
  w[l].push({ gtag_js: new Date() });
  w[l].push({ gtag_config: i });

  var f = d.getElementsByTagName(s)[0],
    j = d.createElement(s);
  j.async = true;
  j.src = 'https://www.googletagmanager.com/gtag/js?id=' + i;
  f.parentNode.insertBefore(j, f);

  window.dataLayer = w[l];
  window.gtag = function () {
    w[l].push(arguments);
  };
  window.gtag('js', new Date());
  window.gtag('config', i);
})(window, document, 'script', 'dataLayer', 'AW-17695033760');
