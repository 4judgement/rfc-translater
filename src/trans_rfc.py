
import os
import re
import json
import time
from googletrans import Translator as GoogleTranslater # pip install googletrans
from tqdm import tqdm # pip install tqdm
from datetime import datetime, timedelta, timezone
CST = timezone(timedelta(hours=+8), 'CST')
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException

# ルールは必ず小文字で登録すること
trans_rules = {
    'abstract': '摘要',
    'introduction': '介绍',
    'acknowledgement': '致谢',
    'acknowledgements': '致谢',
    'status of this memo': '本备忘录的状态',
    'copyright notice': '著作权',
    'table of contents': '目录',
    'conventions': '公约',
    'terminology': '术语',
    'discussion': '讨论',
    'references': '参考文献',
    'normative references': '引用文献',
    'informative references': '参考引用',
    'contributors': '贡献者',
    'where': 'ただし|哪儿',
    'where:': 'ただし：|哪儿：',
    'assume:': '假设：',
    "the key words \"must\", \"must not\", \"required\", \"shall\", "
    "\"shall not\", \"should\", \"should not\", \"recommended\", \"may\", and"
    " \"optional\" in this document are to be interpreted as described in rfc"
    " 2119 [rfc2119].":
        "关键字 \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\","
        " \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", 和 \"OPTIONAL\""
        " 应按照 rfc 2119 [rfc2119] 中的描述进行解释。",
    "the key words \"must\", \"must not\", \"required\", \"shall\","
    " \"shall not\", \"should\", \"should not\", \"recommended\","
    " \"not recommended\", \"may\", and \"optional\" in this document are to be"
    " interpreted as described in bcp 14 [rfc2119] [rfc8174] when, and only when"
    ", they appear in all capitals, as shown here.":
        "关键字 \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\","
        " \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", 和 \"OPTIONAL\""
        " 当且仅当它们以所有大写字母出现时，应按照 bcp 14 [rfc2119] [rfc8174] 中的描述进"
        "行解释，如此处所示。",
    "this document is subject to bcp 78 and the ietf trust's legal provisions"
    " relating to ietf documents (https://trustee.ietf.org/license-info) in"
    " effect on the date of publication of this document. please review these"
    " documents carefully, as they describe your rights and restrictions with"
    " respect to this document. code components extracted from this document"
    " must include simplified bsd license text as described in section 4.e of"
    " the trust legal provisions and are provided without warranty as described"
    " in the simplified bsd license.":
        "本文件受 bcp 78 和 ietf 信托关于 ietf 文件"
        " (https://trustee.ietf.org/license-info) 的法律规定的约束，在本文件发布之日"
        "生效。请仔细阅读这些文件，因为它们描述了您对本文件的权利和限制。从本文档中提取的代码"
        "组件必须包含信托法律条款第 4.e 节中所述的简化 bsd 许可文本，并且不提供如简化 bsd "
        "许可中所述的保证。",
}


# 每次翻译多少个段落。
CHUNK_NUM = 15


class TransMode:
    PY_GOOGLETRANS = 1
    SELENIUM_GOOGLE = 2


# 翻訳抽象クラス
class Translator:

    def __init__(self, total, desc='zh-cn'):
        self.count = 0
        self.total = total
        # プログレスバー
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)

    def increment_count(self, incr=1):
        # プログレスバー用の出力
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        # プログレスバーに詳細情報を追加
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))

    def close(self):
        return True


class TranslatorGoogletrans(Translator):
    # py-googletrans

    def __init__(self, total, desc='zh-cn'):
        super(TranslatorGoogletrans, self).__init__(total, desc)

        self.translator = GoogleTranslater()

    def translate(self, text, dest='zh-cn'):
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        cn = trans_rules.get(text.lower())
        if cn:
            return cn
        # URLエンコード処理でエラー回避用に、&の後ろに空白を入れる
        text = re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text)
        # 翻訳処理
        cn = self.translator.translate(text, dest=dest)
        # 翻訳の間隔を開ける
        wait_time = 3 + len(text) / 100  # IMPORTANT!!!
        # プログレスバーに詳細情報を追加
        self.output_progress(len=len(text), wait_time=wait_time)
        time.sleep(wait_time)
        return cn.text

    def translate_texts(self, texts, dest='zh-cn'):
        # URLエンコード処理でエラー回避用に、&の後ろに空白を入れる
        texts = list(map(lambda text: re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text), texts))
        # 翻译流程

        # 这里不要使用 bluk translate 的方式，https://github.com/ssut/py-googletrans/issues/264
        # 在 上游修复前 锁定 googletrans==3.1.0a0 版本
        texts_cn = [self.translator.translate(t, dest=dest) for t in texts]
        res = [text_cn.text for text_cn in texts_cn]
        total_len = sum([len(t) for t in texts])
        # 防封号
        wait_time = 5 + total_len / 1000  # IMPORTANT!!
        # プログレスバーに詳細情報を追加
        self.output_progress(len=total_len, wait_time=wait_time)
        time.sleep(wait_time)
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        for i, text in enumerate(texts):
            cn = trans_rules.get(text.lower())
            if cn:
                res[i] = cn
        # 括号转换为全角（） -> ()
        res = [re.sub(r'（）', '()', text_cn) for text_cn in res]
        return res


class TranslatorSeleniumGoogletrans(Translator):
    # Selenium + Google

    def __init__(self, total, desc=''):
        super(TranslatorSeleniumGoogletrans, self).__init__(total, desc)

        WEBDRIVER_EXE_PATH = os.getenv('WEBDRIVER_EXE_PATH',
            default='C:\Apps\webdriver\geckodriver.exe')
        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Firefox(executable_path=WEBDRIVER_EXE_PATH, options=options)
        browser.implicitly_wait(3)
        self._browser = browser

    def translate(self, text, dest='zh-cn'):
        if len(text) == 0:
            return ""
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        # 「%」をURLエンコードする
        text = text.replace('%', '%25')
        # 「|」をURLエンコードする
        text = text.replace('|', '%7C')
        # 「/」をURLエンコードする
        text = text.replace('/', '%2F')

        browser = self._browser
        # 翻訳したい文をURLに埋め込んでからアクセスする
        text_for_url = urllib.parse.quote_plus(text, safe='')
        url = "https://translate.google.com/#en/zh-cn/{0}".format(text_for_url)
        browser.get(url)
        # 数秒待機する
        wait_time = 3 + len(text) / 1000
        time.sleep(wait_time)
        # 翻訳結果を抽出する
        elems = browser.find_elements_by_css_selector("span[jsname='W297wb']")
        ja = "".join(elem.text for elem in elems)
        # プログレスバーに詳細情報を追加
        self.output_progress(len=len(text), wait_time=wait_time)
        return ja

    def translate_texts(self, texts, dest='zh-cn'):
        res = []
        for text in texts:
            cn = self.translate(text, dect=dest)
            res.append(cn)
            self.increment_count()
        return res

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def trans_rfc(number, mode):

    input_dir = 'data/%04d' % (number//1000%10*1000)
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)
    midway_file = '%s/rfc%d-midway.json' % (input_dir, number)

    if os.path.isfile(midway_file):  # 途中まで翻訳済みのファイルがあれば復元する
        with open(midway_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)
    else:
        with open(input_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)

    desc = 'RFC %d' % number
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=len(obj['contents']), desc=desc)
    else:
        translator = TranslatorSeleniumGoogletrans(total=len(obj['contents']), desc=desc)
    is_canceled = False

    try:
        # title ｜ 标题
        if not obj['title'].get('zh-cn'):  # 跳过已经翻译的段落
            titles = obj['title']['text'].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj['title']['zh-cn'] = "RFC %d" % number
            else:
                text = titles[1]
                cn = translator.translate(text)
                obj['title']['zh-cn'] = "RFC %d - %s" % (number, cn)

        # batch translate contents | 批量翻译
        for obj_contents in chunks(list(enumerate(obj['contents'])), CHUNK_NUM):

            texts = []  # origin text | 原文
            pre_texts = []  # 文字前的符号 ｜ 原文の前文字 (箇条書きの記号など)

            for i, content in obj_contents:

                # do not do duplicate translate | 已经有的段落不需要翻译
                if (content.get('zh-cn')
                        or (content.get('raw') is True)):
                    texts.append('')
                    pre_texts.append('')
                    continue

                text = content['text']

                # 一些重点段落前会有标志性的字符，排除这些字符的影响。
                # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
                pattern = r'^([\-o\*\+\$]' \
                          r' |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})?' \
                          r' |\(?[0-9a-z]\)' \
                          r' |\[[0-9a-z]{1,2}\]' \
                          r' |[a-z]\. )(.*)$'
                m = re.match(pattern, text)
                if m:
                    pre_texts.append(m[1])
                    texts.append(m[2])
                else:
                    pre_texts.append('')
                    texts.append(text)

            if mode == TransMode.PY_GOOGLETRANS:
                translator.increment_count(len(texts))

            texts_cn = translator.translate_texts(texts)

            # 翻译结果
            for (i, content), pre_text, text_cn in \
                    zip(obj_contents, pre_texts, texts_cn):
                obj['contents'][i]['zh-cn'] = pre_text + text_cn

        print("[+] batch translate", flush=True)

    except json.decoder.JSONDecodeError as e:
        print('[-] googletrans is blocked by Google :(')
        print('[-]', datetime.now(CST))
        is_canceled = True
    except NoSuchElementException as e:
        print('[-] Google Translate is blocked by Google :(')
        print('[-]', datetime.now(CST))
        is_canceled = True
    except KeyboardInterrupt as e:
        print('Interrupted!')
        is_canceled = True
    finally:
        translator.close()

    if not is_canceled:
        with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        # 删除不必要的文件
        os.remove(input_file)
        if os.path.isfile(midway_file):
            os.remove(midway_file)
        return True
    else:
        with open(midway_file, 'w', encoding="utf-8", newline="\n") as f:
            # 中间文件
            json.dump(obj, f, indent=2, ensure_ascii=False)
        return False


# c测试 翻译
def trans_test(mode=TransMode.SELENIUM_GOOGLE):
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=1)
        cn = translator.translate('test', dest='zh-cn')
        return cn == '测试'
    else:
        translator = TranslatorSeleniumGoogletrans(total=1)
        cn = translator.translate('test', dest='zh-cn')
        print('result:', cn)
        return cn == '测试'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(total=1)
    parser.add_argument('text', help='english text')
    args = parser.parse_args()

    translator = TranslatorGoogletrans(total=1)
    cn = translator.translate(args.text, dest='zh-cn')
    print(cn)


# googletrans:
# 連続してアクセスすると、以下のメッセージが表示されてIPアドレス単位でブロックされるので注意。
#
#
#   お使いのコンピュータ ネットワークから通常と異なるトラフィックが検出されました。
#   後でもう一度リクエストを送信してみてください。このページが表示された理由
#
#   このページは、お使いのコンピュータ ネットワークから利用規約に違反すると考えられる
#   リクエストが自動検出されたときに表示されます。
#   ブロックは、これらのリクエストが停止されると間もなく解除されます。
#
#   このトラフィックは、リクエストを自動送信する不正なソフトウェア、ブラウザ プラグイン、
#   またはスクリプトによって発生した可能性があります。ネットワーク接続が共有のものである場合は、
#   同じ IP アドレスを使用している別のコンピュータが発生元の可能性がありますので、
#   管理者に相談してください。詳しくはこちらをご覧ください。
#
#   ロボットが使用するような高度な検索語を使用したり、リクエストを非常にすばやく送信した場合も、
#   このページが表示されることがあります。
#
#   IP アドレス: XX.XX.XX.XX
#   時間: 2019-10-16T03:56:15Z
#   URL: https://translate.google.com/translate_a/single?...
#
#
