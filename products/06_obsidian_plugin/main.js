const { Plugin, Notice, requestUrl } = require('obsidian');

const API_BASE = 'https://lenin-book.v2.site/api/v1';

module.exports = class LeninSearchPlugin extends Plugin {
  async onload() {
    // === lenin-search: поиск по корпусу ===
    this.addCommand({
      id: 'lenin-search',
      name: 'Поиск по Ленину',
      editorCallback: async (editor) => {
        const sel = editor.getSelection() || '';
        const query = sel || await this.prompt('Запрос для поиска по Ленину:');
        if (!query) return;
        new Notice(`Ищу: ${query}...`);
        try {
          const r = await requestUrl(`${API_BASE}/search?q=${encodeURIComponent(query)}&n=5`);
          const data = r.json;
          if (data.results?.length) {
            const prefix = sel ? '' : `**${query}**\n\n`;
            const md = prefix + data.results.map((c, i) =>
              `> «${c.text?.slice(0, 300) || ''}»\n> — В.И. Ленин, ${c.year || '?'}, т. ${c.volume || '?'} *(релевантность: ${Math.round((c.score || 0) * 100)}%)*\n`
            ).join('\n');
            editor.replaceSelection(md);
            new Notice(`Найдено ${data.results.length} цитат`);
          } else {
            new Notice('Ничего не найдено');
          }
        } catch (e) { new Notice(`Ошибка: ${e.message}`); }
      }
    });

    // === lenin-link: авто-линковка концепта ===
    this.addCommand({
      id: 'lenin-link',
      name: 'Инфо о концепте',
      editorCallback: async (editor) => {
        const word = editor.getSelection() || await this.prompt('Концепт:');
        if (!word) return;
        new Notice(`Ищу концепт: ${word}...`);
        try {
          const r = await requestUrl(`${API_BASE}/concept/${encodeURIComponent(word)}`);
          const data = r.json;
          if (data.name) {
            const md = `**${data.name}**\n- Упоминаний: ${data.frequency || '—'}\n- Пик: ${data.peak_year || '—'}\n- Кластер: ${data.cluster || '—'}\n- Связи: ${(data.connections || []).slice(0, 5).join(', ') || '—'}\n`;
            editor.replaceSelection(md);
            new Notice(`Концепт: ${data.name}`);
          } else {
            new Notice(`Концепт "${word}" не найден`);
          }
        } catch (e) { new Notice(`Ошибка: ${e.message}`); }
      }
    });

    // === lenin-quote: случайная цитата ===
    this.addCommand({
      id: 'lenin-quote',
      name: 'Случайная цитата Ленина',
      editorCallback: async (editor) => {
        new Notice('Загружаю цитату...');
        try {
          const r = await requestUrl(`${API_BASE}/quotes?n=1`);
          const data = r.json;
          const q = data.quotes?.[0] || data[0];
          if (q) {
            const md = `> «${q.text?.slice(0, 400) || ''}»\n> — В.И. Ленин, ${q.year || '?'}, т. ${q.volume || '?'}\n`;
            editor.replaceSelection(md);
            new Notice('Цитата вставлена');
          }
        } catch (e) { new Notice(`Ошибка: ${e.message}`); }
      }
    });
  }

  async prompt(msg) {
    // Fallback: use window.prompt (simple but works)
    return window.prompt(msg);
  }
};
