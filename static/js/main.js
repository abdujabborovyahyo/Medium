// ==========================================
// 1. CSRF TOKEN HELPER (Django xavfsizligi)
// ==========================================
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrftoken = getCookie("csrftoken");

// Anonymous users get redirected to the login page by @login_required.
// fetch() follows that redirect and receives HTML, so send them to the login page instead.
function parseJsonOrLogin(res) {
  const type = res.headers.get("content-type") || "";
  if (res.redirected || !type.includes("application/json")) {
    window.location.href = "/accounts/login/?next=" + encodeURIComponent(window.location.pathname);
    return Promise.reject(new Error("Login required"));
  }
  return res.json();
}

// ==========================================
// 2. TUGMALAR UCHUN BOSISH (CLICK) HODISALARI
// ==========================================
document.addEventListener("click", function (e) {

  // A. LAYK TUGMASI (Like Toggle)
  const likeBtn = e.target.closest("[data-like-btn]");
  if (likeBtn) {
    const articleId = likeBtn.dataset.articleId;
    fetch(`/interactions/like-toggle/${articleId}/`, {
      method: "POST",
      headers: {"X-CSRFToken": csrftoken, "Accept": "application/json"},
      credentials: "same-origin",
    })
      .then(parseJsonOrLogin)
      .then(data => {
        if (data.liked) likeBtn.classList.add("liked"); else likeBtn.classList.remove("liked");
        const countEl = likeBtn.querySelector(".count");
        if (countEl) countEl.textContent = data.count;
      })
      .catch(err => console.error("Like toggle failed:", err));
  }

  // B. SAQLASH TUGMASI (Bookmark Toggle)
  const bBtn = e.target.closest("[data-bookmark-btn]");
  if (bBtn) {
    const id = bBtn.dataset.articleId || bBtn.getAttribute("data-article-id");
    if (!id) return;
    fetch(`/interactions/bookmark-toggle/${id}/`, {
      method: "POST",
      headers: {"X-CSRFToken": csrftoken, "Accept": "application/json"},
      credentials: "same-origin",
    })
    .then(parseJsonOrLogin)
    .then(data => {
      if (data.saved) bBtn.classList.add("saved"); else bBtn.classList.remove("saved");
    })
    .catch(err => console.error("Bookmark toggle failed:", err));
  }

  // C. XATCHO'PDAN O'CHIRISH TUGMASI (Remove Bookmark)
  const removeBookmarkBtn = e.target.closest("[data-remove-bookmark]");
  if (removeBookmarkBtn) {
    const id = removeBookmarkBtn.dataset.articleId || removeBookmarkBtn.getAttribute("data-article-id");
    if (!id) return;
    fetch(`/interactions/bookmark-toggle/${id}/`, {
      method: "POST",
      headers: {"X-CSRFToken": csrftoken, "Accept": "application/json"},
      credentials: "same-origin",
    }).then(parseJsonOrLogin).then(data => {
        if (!data.saved) {
          const card = removeBookmarkBtn.closest(".card");
          if (card) card.remove();
        }
    }).catch(err => console.error("Remove bookmark failed", err));
  }

  // D. RO'YXATGA QO'SHISH (Add to List)
  const addToListBtn = e.target.closest("[data-add-to-list]");
  if (addToListBtn) {
    const articleId = addToListBtn.dataset.articleId || addToListBtn.getAttribute("data-article-id");
    if (!articleId) return;
    const listName = prompt("Enter a list name to save this story (existing lists will be reused):", "");
    if (listName === null || !listName.trim()) return;
    const form = new FormData();
    form.append("article_id", articleId);
    form.append("list_name", listName);

    fetch("/interactions/add-to-list/", {
      method: "POST",
      body: form,
      headers: {"X-CSRFToken": csrftoken},
      credentials: "same-origin",
    }).then(parseJsonOrLogin)
      .then(data => {
        if (data && data.success) {
          alert(`Saved to list "${data.list_name}".`);
        } else {
          alert(data.error || "Could not save to list.");
        }
      })
      .catch(err => {
        console.error("Add to list failed", err);
        alert("Could not save to a list.");
      });
  }

  // E. RO'YXATDAN O'CHIRISH (Remove from List)
  const removeFromListBtn = e.target.closest("[data-remove-from-list]");
  if (removeFromListBtn) {
    const articleId = removeFromListBtn.dataset.articleId || removeFromListBtn.getAttribute("data-article-id");
    const listId = removeFromListBtn.dataset.listId || removeFromListBtn.getAttribute("data-list-id");
    if (!articleId || !listId) return;
    const form = new FormData();
    form.append("article_id", articleId);
    form.append("list_id", listId);

    fetch("/interactions/remove-from-list/", {
      method: "POST",
      body: form,
      headers: {"X-CSRFToken": csrftoken},
      credentials: "same-origin",
    }).then(parseJsonOrLogin)
      .then(data => {
        if (data && data.success) {
          const card = removeFromListBtn.closest(".card");
          if (card) card.remove();
        } else {
          alert(data.error || "Could not remove from list.");
        }
      })
      .catch(err => {
        console.error("Remove from list failed", err);
        alert("Could not remove from list.");
      });
  }

  // F. FOLLOW TUGMASI (Follow Toggle)
  const followBtn = e.target.closest("#follow-btn");
  if (followBtn) {
    const authorId = followBtn.dataset.authorId;
    if (!authorId) return;

    fetch(`/notifications/follow/${authorId}/`, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrftoken,
      },
      credentials: "same-origin",
    })
      .then(parseJsonOrLogin)
      .then((data) => {
        if (data.error) {
          alert(data.error);
          return;
        }
        if (data.is_following) {
          followBtn.textContent = "Following";
          followBtn.classList.add("following");
        } else {
          followBtn.textContent = "Follow";
          followBtn.classList.remove("following");
        }
        if (typeof loadNotificationsBadge === "function") {
          loadNotificationsBadge();
        }
      })
      .catch((err) => {
        console.error("Follow failed:", err);
        alert("Failed to update follow status. Please try again.");
      });
  }
});

// ==========================================
// 3. NOTIFICATIONS (o'qilmagan bildirishnomalar badge'i va dropdown)
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
  const notifBtn = document.getElementById("notifications-btn");
  const notifMenu = document.getElementById("notifications-menu");
  if (notifBtn && notifMenu) {
    notifBtn.addEventListener("click", function (e) {
      e.preventDefault();
      notifMenu.style.display = notifMenu.style.display === "none" ? "block" : "none";
    });
    document.addEventListener("click", function (e) {
      if (!notifBtn.parentElement.contains(e.target)) notifMenu.style.display = "none";
    });
  }

  // Count a "read" when the reader reaches the end of an article
  // after spending some time on the page (not just a fast scroll).
  const readMarker = document.querySelector("[data-read-url]");
  if (readMarker && "IntersectionObserver" in window) {
    const observer = new IntersectionObserver(function (entries) {
      if (!entries[0].isIntersecting) return;
      observer.disconnect();
      fetch(readMarker.dataset.readUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken || readMarker.dataset.csrf },
        credentials: "same-origin",
      }).catch(() => {});
    });
    // Start watching only after 10 seconds on the page
    setTimeout(function () { observer.observe(readMarker); }, 10000);
  }

  // "Show password" checkbox on login / signup forms
  document.querySelectorAll("[data-toggle-password]").forEach(function (box) {
    box.addEventListener("change", function () {
      box.closest("form").querySelectorAll("input[name^='password']").forEach(function (input) {
        input.type = box.checked ? "text" : "password";
      });
    });
  });

  function loadNotificationsBadge() {
    if (!document.getElementById("notif-badge")) return;  // anonymous user
    fetch("/notifications/unread-count/", {credentials: "same-origin"})
      .then(res => res.json())
      .then(data => {
        const badge = document.getElementById("notif-badge");
        if (!badge) return;
        if (data.unread_count > 0) {
          badge.textContent = data.unread_count;
          badge.style.display = "inline-block";
        } else {
          badge.style.display = "none";
        }
      })
      .catch(() => {});
  }

  // Sahifa yuklanganda badge ni yangilash
  loadNotificationsBadge();

  // Har 60 soniyada avtomatik yangilash
  setInterval(loadNotificationsBadge, 60000);

  // Global scope ga chiqarish (follow tugmasi uchun)
  window.loadNotificationsBadge = loadNotificationsBadge;
});
