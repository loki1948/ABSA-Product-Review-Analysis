"""Assemble docs/report_site/index.html from source.html, lit.html and litcmp.html.

Citations are written as {{c:key}} and numbered in order of first appearance (IEEE style).
Run: python docs/report_site/build.py
"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

INTROSTAT = (
    "A study by the Spiegel Research Center found that the purchase likelihood for a product "
    "with five reviews is 270% greater than for a product with none {{c:spiegel2017}}, and a 2025 "
    "survey of 1,026 adults in the United States found that only 4% of consumers never read online "
    "reviews of businesses {{c:brightlocal2025}}."
)

REFS = {
    "spiegel2017": 'Spiegel Research Center, "How online reviews influence sales: Evidence of the power of online reviews to shape customer behavior," Medill School of Journalism, Northwestern Univ., Evanston, IL, USA, 2017. [Online]. Available: https://spiegel.medill.northwestern.edu/how-online-reviews-influence-sales/',
    "brightlocal2025": 'BrightLocal, "Local consumer review survey 2025," Jan. 2025. [Online]. Available: https://www.brightlocal.com/research/local-consumer-review-survey-2025/',
    "pontiki2014": 'M. Pontiki, D. Galanis, J. Pavlopoulos, H. Papageorgiou, I. Androutsopoulos, and S. Manandhar, "SemEval-2014 Task 4: Aspect based sentiment analysis," in <i>Proc. 8th Int. Workshop Semantic Evaluation (SemEval 2014)</i>, Dublin, Ireland, 2014, pp. 27&ndash;35, doi: 10.3115/v1/S14-2004.',
    "zhang2023survey": 'W. Zhang, X. Li, Y. Deng, L. Bing, and W. Lam, "A survey on aspect-based sentiment analysis: Tasks, methods, and challenges," <i>IEEE Trans. Knowl. Data Eng.</i>, vol. 35, no. 11, pp. 11019&ndash;11038, Nov. 2023, doi: 10.1109/TKDE.2022.3230975.',
    "hu2004": 'M. Hu and B. Liu, "Mining and summarizing customer reviews," in <i>Proc. 10th ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining (KDD &rsquo;04)</i>, Seattle, WA, USA, 2004, pp. 168&ndash;177, doi: 10.1145/1014052.1014073.',
    "brauwers2022": 'G. Brauwers and F. Frasincar, "A survey on aspect-based sentiment classification," <i>ACM Comput. Surv.</i>, vol. 55, no. 4, Art. no. 65, 2022, doi: 10.1145/3503044.',
    "nazir2022": 'A. Nazir, Y. Rao, L. Wu, and L. Sun, "Issues and challenges of aspect-based sentiment analysis: A comprehensive survey," <i>IEEE Trans. Affect. Comput.</i>, vol. 13, no. 2, pp. 845&ndash;863, 2022, doi: 10.1109/TAFFC.2020.2970399.',
    "li2021": 'R. Li, H. Chen, F. Feng, Z. Ma, X. Wang, and E. Hovy, "Dual graph convolutional networks for aspect-based sentiment analysis," in <i>Proc. 59th Annu. Meeting Assoc. Comput. Linguistics (ACL-IJCNLP)</i>, 2021, pp. 6319&ndash;6329, doi: 10.18653/v1/2021.acl-long.494.',
    "tian2021": 'Y. Tian, G. Chen, and Y. Song, "Aspect-based sentiment analysis with type-aware graph convolutional networks and layer ensemble," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT)</i>, 2021, pp. 2910&ndash;2922, doi: 10.18653/v1/2021.naacl-main.231.',
    "sun2019": 'C. Sun, L. Huang, and X. Qiu, "Utilizing BERT for aspect-based sentiment analysis via constructing auxiliary sentence," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT)</i>, Minneapolis, MN, USA, 2019, pp. 380&ndash;385, doi: 10.18653/v1/N19-1035.',
    "xu2019": 'H. Xu, B. Liu, L. Shu, and P. Yu, "BERT post-training for review reading comprehension and aspect-based sentiment analysis," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT)</i>, Minneapolis, MN, USA, 2019, pp. 2324&ndash;2335, doi: 10.18653/v1/N19-1242.',
    "dai2021": 'J. Dai, H. Yan, T. Sun, P. Liu, and X. Qiu, "Does syntax matter? A strong baseline for aspect-based sentiment analysis with RoBERTa," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT)</i>, 2021, pp. 1816&ndash;1829, doi: 10.18653/v1/2021.naacl-main.146.',
    "seoh2021": 'R. Seoh, I. Birle, M. Tak, H.-S. Chang, B. Pinette, and A. Hough, "Open aspect target sentiment classification with natural language prompts," in <i>Proc. Conf. Empirical Methods Natural Lang. Process. (EMNLP)</i>, 2021, pp. 6311&ndash;6322, doi: 10.18653/v1/2021.emnlp-main.509.',
    "yan2021": 'H. Yan, J. Dai, T. Ji, X. Qiu, and Z. Zhang, "A unified generative framework for aspect-based sentiment analysis," in <i>Proc. 59th Annu. Meeting Assoc. Comput. Linguistics (ACL-IJCNLP)</i>, 2021, pp. 2416&ndash;2429, doi: 10.18653/v1/2021.acl-long.188.',
    "zhang2021gas": 'W. Zhang, X. Li, Y. Deng, L. Bing, and W. Lam, "Towards generative aspect-based sentiment analysis," in <i>Proc. 59th Annu. Meeting Assoc. Comput. Linguistics (ACL-IJCNLP), Vol. 2: Short Papers</i>, 2021, pp. 504&ndash;510, doi: 10.18653/v1/2021.acl-short.64.',
    "gou2023": 'Z. Gou, Q. Guo, and Y. Yang, "MvP: Multi-view prompting improves aspect sentiment tuple prediction," in <i>Proc. 61st Annu. Meeting Assoc. Comput. Linguistics (ACL)</i>, Toronto, Canada, 2023, pp. 4380&ndash;4397, doi: 10.18653/v1/2023.acl-long.240.',
    "scaria2024": 'K. Scaria, H. Gupta, S. Goyal, S. Sawant, S. Mishra, and C. Baral, "InstructABSA: Instruction learning for aspect based sentiment analysis," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT), Vol. 2: Short Papers</i>, Mexico City, Mexico, 2024, pp. 720&ndash;736, doi: 10.18653/v1/2024.naacl-short.63.',
    "wang2023": 'Z. Wang, Q. Xie, Y. Feng, Z. Ding, Z. Yang, and R. Xia, "Is ChatGPT a good sentiment analyzer? A preliminary study," 2023, <i>arXiv:2304.04339</i>.',
    "zhang2024": 'W. Zhang, Y. Deng, B. Liu, S. J. Pan, and L. Bing, "Sentiment analysis in the era of large language models: A reality check," in <i>Findings Assoc. Comput. Linguistics: NAACL 2024</i>, Mexico City, Mexico, 2024, pp. 3881&ndash;3906, doi: 10.18653/v1/2024.findings-naacl.246.',
    "devlin2019": 'J. Devlin, M.-W. Chang, K. Lee, and K. Toutanova, "BERT: Pre-training of deep bidirectional transformers for language understanding," in <i>Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics (NAACL-HLT)</i>, Minneapolis, MN, USA, 2019, pp. 4171&ndash;4186, doi: 10.18653/v1/N19-1423.',
    "loshchilov2019": 'I. Loshchilov and F. Hutter, "Decoupled weight decay regularization," in <i>Proc. 7th Int. Conf. Learn. Represent. (ICLR)</i>, New Orleans, LA, USA, 2019.',
    "wolf2020": 'T. Wolf <i>et al.</i>, "Transformers: State-of-the-art natural language processing," in <i>Proc. Conf. Empirical Methods Natural Lang. Process.: System Demonstrations (EMNLP)</i>, 2020, pp. 38&ndash;45, doi: 10.18653/v1/2020.emnlp-demos.6.',
}


def main() -> None:
    html = (HERE / "source.html").read_text(encoding="utf-8")
    html = html.replace("{{INTROSTAT}}", INTROSTAT)
    html = html.replace("{{LIT}}", (HERE / "lit.html").read_text(encoding="utf-8"))
    html = html.replace("{{LITCMP}}", (HERE / "litcmp.html").read_text(encoding="utf-8"))
    html = html.replace("{{c:zhang2022survey}}", "{{c:zhang2023survey}}")

    order: list[str] = []

    def number(match: re.Match) -> str:
        key = match.group(1)
        if key not in REFS:
            raise KeyError(f"unknown citation {key}")
        if key not in order:
            order.append(key)
        n = order.index(key) + 1
        return f'<a class="cite" href="#ref-{n}">[{n}]</a>'

    html = re.sub(r"\{\{c:([a-z0-9]+)\}\}", number, html)
    unused = set(REFS) - set(order)
    if unused:
        raise ValueError(f"references never cited: {unused}")
    items = "\n".join(
        f'<li id="ref-{i}"><span class="rn">[{i}]</span><span>{REFS[k]}</span></li>' for i, k in enumerate(order, 1)
    )
    html = html.replace("{{REFS}}", f'<ol class="refs">\n{items}\n</ol>')
    assert "{{" not in html, re.findall(r"\{\{[^}]*\}\}", html)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"index.html written, {len(order)} references")


if __name__ == "__main__":
    main()
