// Article editor page (articles/article_form.html): Quill editor, cover preview, image upload.
(function () {
  const form = document.getElementById("article-form");
  if (!form || typeof Quill === "undefined") return;
  const coverInput = document.getElementById("id_cover_image");
  const hiddenBodyInput = document.getElementById("id_body");

  // Cover image preview
  coverInput.addEventListener("change", function (e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (event) {
      const preview = document.getElementById("cover-preview");
      preview.innerHTML = "";
      const img = document.createElement("img");
      img.src = event.target.result;
      img.alt = "cover";
      preview.appendChild(img);
    };
    reader.readAsDataURL(file);
  });

  // Quill editor
  const quill = new Quill("#quill-editor", {
    theme: "snow",
    placeholder: "Write your article here...",
    modules: {
      toolbar: {
        container: [
          [{ header: [1, 2, 3, false] }],
          ["bold", "italic", "underline", "strike"],
          ["link", "image", "video", "blockquote", "code-block"],
          [{ list: "ordered" }, { list: "bullet" }],
          [{ align: [] }],
          ["clean"]
        ],
        handlers: { image: uploadImage }
      }
    }
  });

  // Images are uploaded to the server instead of being stored as huge base64 strings
  function uploadImage() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/jpeg,image/png,image/gif,image/webp";
    input.onchange = function () {
      const file = input.files[0];
      if (!file) return;
      const data = new FormData();
      data.append("file", file);
      fetch(form.dataset.uploadUrl, {
        method: "POST",
        body: data,
        headers: { "X-CSRFToken": csrftoken },
        credentials: "same-origin"
      })
        .then(parseJsonOrLogin)
        .then(function (res) {
          if (res.error) { alert(res.error); return; }
          const range = quill.getSelection(true);
          quill.insertEmbed(range.index, "image", res.url, "user");
          quill.setSelection(range.index + 1);
        })
        .catch(function () { alert("Image upload failed. Please try again."); });
    };
    input.click();
  }

  // Edit mode / re-rendered form: load the existing content
  if (hiddenBodyInput.value) {
    quill.root.innerHTML = hiddenBodyInput.value;
  }

  form.addEventListener("submit", function () {
    hiddenBodyInput.value = quill.getText().trim() || quill.root.querySelector("img,iframe")
      ? quill.root.innerHTML
      : "";
  });
})();
