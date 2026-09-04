// Shared in-place (AJAX) month/day navigation for the calendar widget on the
// main list page and the client page. Both pages render a #calendar-container
// element carrying a Thymeleaf fragment; this script intercepts clicks on
// calendar links, fetches the fragment, and swaps it in without a full reload.
function initCalendarNav(options) {
    options = options || {};
    var linkSelector = options.linkSelector || 'a.calendar-nav';
    var shouldIntercept = options.shouldIntercept || function () { return true; };
    var afterLoad = options.afterLoad || function () {};

    // Guards against out-of-order responses: if two fetches are in flight (e.g.
    // a double-click on the nav arrow) and they resolve out of order, only the
    // response to the most recently issued request is applied.
    var latestRequestId = 0;

    function bindContainer(container) {
        container.addEventListener('click', function (e) {
            var link = e.target.closest(linkSelector);
            if (!link || !shouldIntercept(link)) return;
            e.preventDefault();
            loadCalendar(link.getAttribute('href'), true);
        });
    }

    function loadCalendar(url, pushState) {
        var requestId = ++latestRequestId;
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(function (res) {
                if (!res.ok) { throw new Error('Calendar request failed: ' + res.status); }
                return res.text();
            })
            .then(function (html) {
                if (requestId !== latestRequestId) return;
                var temp = document.createElement('div');
                temp.innerHTML = html.trim();
                var newContainer = temp.firstElementChild;
                document.getElementById('calendar-container').replaceWith(newContainer);
                bindContainer(newContainer);
                afterLoad(newContainer);
                if (pushState) {
                    history.pushState({ calendarUrl: url }, '', url);
                }
            })
            .catch(function () {
                // Fall back to a real navigation rather than leaving the calendar
                // stuck or corrupting the DOM with an error page's markup.
                window.location.href = url;
            });
    }

    bindContainer(document.getElementById('calendar-container'));

    window.addEventListener('popstate', function () {
        loadCalendar(location.pathname + location.search, false);
    });
}
