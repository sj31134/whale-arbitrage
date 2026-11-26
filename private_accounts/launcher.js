// Read the Mac shortcut inside this tab. Its contents are never submitted.
const shortcut = document.querySelector("#mac-shortcut");
shortcut.addEventListener("change", async () => {
  const error = document.querySelector("#shortcut-error");
  try {
    const file = shortcut.files[0];
    if (!file || file.size > 16384) throw new Error();
    const plist = new DOMParser().parseFromString(await file.text(), "application/xml");
    const key = Array.from(plist.querySelectorAll("plist > dict > key"))
      .find(node => node.textContent === "URL");
    const value = key?.nextElementSibling;
    if (value?.localName !== "string") throw new Error();
    const target = new URL(value.textContent);
    if (target.protocol !== "http:" || target.hostname !== "127.0.0.1" ||
        target.username || target.password || target.search || target.hash ||
        !/^\/[0-9a-f]{64}\/desk\/manager$/.test(target.pathname)) throw new Error();
    location.replace(target.pathname);
  } catch {
    error.textContent = "이 프로젝트에서 생성한 투자 대시보드.webloc 파일을 선택하세요.";
    shortcut.value = "";
  }
});
