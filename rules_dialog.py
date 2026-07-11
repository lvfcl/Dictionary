"""
Окно "Правила" - справочник по базовой грамматике французского языка,
доступный по кнопке в главном окне. Организован как несколько вкладок
(QTabWidget), каждая из которых - статичная HTML-страница в QTextBrowser.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QTextBrowser
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


_ARTICLES_HTML = """
<h2>Артикли и род существительных</h2>

<h3>Неопределенный артикль (какой-то, один из...)</h3>
<ul>
  <li><b>un</b> — мужской род: <i>un chat</i> (кот)</li>
  <li><b>une</b> — женский род: <i>une pomme</i> (яблоко)</li>
  <li><b>des</b> — множественное число (оба рода): <i>des chats, des pommes</i></li>
</ul>

<h3>Определенный артикль (конкретный, уже известный предмет)</h3>
<ul>
  <li><b>le</b> — мужской род: <i>le chat</i></li>
  <li><b>la</b> — женский род: <i>la pomme</i></li>
  <li><b>les</b> — множественное число (оба рода): <i>les chats, les pommes</i></li>
  <li><b>l'</b> — перед словом, начинающимся с гласной или немой h:
      <i>l'ami, l'heure</i> (вместо le ami / la heure)</li>
</ul>
<p><i>Это явление называется элизией — она нужна, чтобы избежать неудобного
стыка двух гласных звуков подряд.</i></p>

<h3>Как определить род существительного</h3>
<p>Точного правила без исключений не существует, но есть частые закономерности
по окончанию слова:</p>
<table cellpadding="4">
<tr><td><b>Чаще мужской род</b></td><td>-age, -ment, -eau, -isme, -phone</td></tr>
<tr><td><b>Чаще женский род</b></td><td>-tion, -sion, -té, -ette, -ance, -ence</td></tr>
</table>
<p>Надежнее всего запоминать род вместе с самим словом (например, сразу как
«la pomme», а не просто «pomme») — именно поэтому в этом словаре артикль
всегда сохраняется вместе со словом.</p>
"""

_PLURAL_HTML = """
<h2>Множественное число</h2>

<h3>Общее правило</h3>
<p>В большинстве случаев множественное число образуется добавлением
буквы <b>-s</b> в конце слова: <i>le livre → les livres</i>.
Важно: эта буква <b>-s</b> почти всегда не произносится на слух —
разница слышна в основном по артиклю (le/la → les).</p>

<h3>Основные исключения</h3>
<ul>
  <li>Слова на <b>-eau, -eu</b> → добавляется <b>-x</b>:
      <i>le bateau → les bateaux, le jeu → les jeux</i></li>
  <li>Слова на <b>-al</b> → чаще всего меняются на <b>-aux</b>:
      <i>le cheval → les chevaux</i></li>
  <li>Слова, уже оканчивающиеся на <b>-s, -x, -z</b>, не меняются вовсе:
      <i>le prix → les prix, la souris → les souris</i></li>
</ul>
"""

_PRONUNCIATION_HTML = """
<h2>Основы произношения</h2>

<h3>Немые буквы</h3>
<p>Конечные согласные <b>чаще всего не произносятся</b>: <i>chat</i>
звучит как [ʃa], без конечного «т». Конечная <b>-e</b> без ударения
тоже обычно не слышна.</p>

<h3>Liaison (связывание слов)</h3>
<p>Если слово оканчивается на согласную, а следующее слово начинается
с гласной, эта согласная иногда "оживает" и произносится, связывая
слова вместе: <i>les amis</i> звучит как [lezami], а не [le ami].</p>

<h3>Носовые гласные</h3>
<p>Сочетания <b>an/am, en/em, in/im, on/om, un/um</b> в конце слога
часто дают носовой звук (воздух частично идет через нос), а не
произносятся как обычная гласная + согласная по отдельности.</p>

<h3>Частые буквосочетания</h3>
<table cellpadding="4">
<tr><td><b>ch</b></td><td>звук «ш» — <i>chat</i> [ʃa]</td></tr>
<tr><td><b>gn</b></td><td>мягкое «нь» — <i>montagne</i></td></tr>
<tr><td><b>ou</b></td><td>звук «у» — <i>vous</i></td></tr>
<tr><td><b>eu / œu</b></td><td>звук между «э» и «ё» — <i>fleur</i></td></tr>
<tr><td><b>gu</b> перед e/i</td><td>твердое «г», h немое не читается — <i>guerre</i></td></tr>
</table>
"""

_TIPS_HTML = """
<h2>Полезные советы для изучения</h2>
<ul>
  <li>Учите существительные сразу вместе с артиклем (<i>la pomme</i>,
      а не просто <i>pomme</i>) — так род запомнится сам собой,
      без отдельного заучивания таблиц.</li>
  <li>Прослушивайте произношение каждого нового слова (кнопка 🔊 в таблице) —
      французское написание часто сильно расходится со звучанием.</li>
  <li>Группируйте слова по папкам (например, «Еда», «Путешествия») —
      так проще повторять слова по темам, а не подряд по алфавиту.</li>
  <li>Используйте режим «Учить слова» регулярно, а не раз в месяц —
      интервальное повторение работает только при частых, но коротких сессиях.</li>
</ul>
"""


class RulesDialog(QDialog):
    """Окно-справочник с базовыми правилами французской грамматики."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Правила французского языка")
        self.resize(650, 550)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        tabs = QTabWidget()
        tabs.setFont(QFont("Arial", 10))

        for title, html in (
            ("Артикли и род", _ARTICLES_HTML),
            ("Множ. число", _PLURAL_HTML),
            ("Произношение", _PRONUNCIATION_HTML),
            ("Советы", _TIPS_HTML),
        ):
            browser = QTextBrowser()
            browser.setFont(QFont("Arial", 11))
            browser.setHtml(html)
            tabs.addTab(browser, title)

        layout.addWidget(tabs)

        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background-color: #E2E8F0;
                color: #4A5568;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4A90E2;
                color: white;
                font-weight: bold;
            }
            QTextBrowser {
                border: none;
                color: #333333;
                padding: 10px;
            }
        """)
