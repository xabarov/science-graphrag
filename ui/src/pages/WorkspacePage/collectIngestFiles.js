const ALLOWED = new Set([".pdf", ".md", ".txt"]);

/**
 * @param {string} name
 * @returns {boolean}
 */
export function isIngestibleFileName(name) {
  const n = String(name || "");
  const i = n.lastIndexOf(".");
  if (i < 0) return false;
  return ALLOWED.has(n.slice(i).toLowerCase());
}

/**
 * @param {FileSystemEntry} entry
 * @returns {Promise<File[]>}
 */
async function walkEntry(entry) {
  if (!entry) return [];
  if (entry.isFile) {
    return new Promise((resolve) => {
      /** @type {FileSystemFileEntry} */
      const fe = entry;
      fe.file(
        (file) => {
          resolve(isIngestibleFileName(file.name) ? [file] : []);
        },
        () => resolve([]),
      );
    });
  }
  if (entry.isDirectory) {
    /** @type {FileSystemDirectoryEntry} */
    const de = entry;
    const reader = de.createReader();
    const out = [];
    const readNext = () =>
      new Promise((resolve) => {
        reader.readEntries(
          async (entries) => {
            resolve(entries);
          },
          () => resolve([]),
        );
      });
    for (;;) {
      const entries = await readNext();
      if (!entries.length) break;
      for (const e of entries) {
        out.push(...(await walkEntry(e)));
      }
    }
    return out;
  }
  return [];
}

/**
 * Build a flat list of ingestible files from a drag-drop ``DataTransfer``.
 * @param {DataTransfer} dt
 * @returns {Promise<File[]>}
 */
export async function collectIngestFilesFromDataTransfer(dt) {
  const list = [];
  if (dt.items && dt.items.length) {
    for (let i = 0; i < dt.items.length; i += 1) {
      const it = dt.items[i];
      if (it.kind !== "file") continue;
      const entry = typeof it.webkitGetAsEntry === "function" ? it.webkitGetAsEntry() : null;
      if (entry) {
        list.push(...(await walkEntry(entry)));
      } else {
        const f = it.getAsFile();
        if (f && isIngestibleFileName(f.name)) list.push(f);
      }
    }
    return list;
  }
  if (dt.files && dt.files.length) {
    for (let i = 0; i < dt.files.length; i += 1) {
      const f = dt.files[i];
      if (f && isIngestibleFileName(f.name)) list.push(f);
    }
  }
  return list;
}
