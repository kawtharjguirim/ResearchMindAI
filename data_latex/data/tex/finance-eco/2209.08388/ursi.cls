% LaTeX 2e class for URSI AT-AP-RASC 2022 extended abstracts, summary papers, and
% student paper competition.
%
% 
%
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{ursi}[2016/08/12 URSI template class]

\DeclareOption{abstract}{%
  \PassOptionsToClass{onecolumn}{article}%
  \PassOptionsToPackage{a4paper,margin=25mm}{geometry}}
\DeclareOption{summary}{%
  \PassOptionsToClass{twocolumn}{article}%
  \PassOptionsToPackage{a4paper,hmargin=16mm,
    vmargin=22mm,columnsep=12mm}{geometry}}
\DeclareOption{spc}{%
  \PassOptionsToClass{onecolumn}{article}%
  \PassOptionsToPackage{a4paper,hmargin=16mm,vmargin=25mm}{geometry}}
\ExecuteOptions{abstract}
\ProcessOptions

% Everything is based on the standard article class
\LoadClass[10pt,a4paper]{article}

% Times font for text and formulas
\RequirePackage[T1]{fontenc}
\RequirePackage{textcomp}
\RequirePackage{mathptmx}

% graphics and formulas
\RequirePackage{graphicx}
\RequirePackage{amsmath}

% Page margins
\RequirePackage{geometry}

% Adjust figure and table captions
\RequirePackage[labelfont=bf,labelsep=period]{caption}


\pagestyle{empty} % no page numbers

% Adjust the section headings
\renewcommand\section{\@startsection{section}{1}{0pt}%
  {0pt plus 3pt}%
  {0.1pt}%
  {\normalfont\fontsize{12}{14}\selectfont\bfseries}}
\renewcommand\subsection{\@startsection{subsection}{2}{0pt}%
  {0pt plus 3pt}%
  {0.1pt}%
  {\normalfont\fontsize{12}{14}\selectfont\bfseries}}

% subsubsections are probably not very useful?
\renewcommand\subsubsection{\@startsection{subsubsection}{3}{0pt}%
  {0pt plus 3pt}%
  {0.1pt}%
  {\normalfont\normalsize\bfseries}}

\if@twocolumn
  \renewcommand\abstractname{\centerline{Abstract}}
\fi

\setlength\parindent{0pt}
\setlength\parskip{12pt plus 3pt minus 1pt}

% Title, author(s) and affiliation(s)
\newcommand\@affiliation{\@empty}
\newcommand\affiliation[1]{\renewcommand\@affiliation{#1}}
\newcounter{affindx}
\newcommand{\aff}[2]{%
  \refstepcounter{affindx}(\theaffindx) #2\\
  \label{aff:#1}%
}

\newcommand{\affref}[1]{$^{(\ref{aff:#1})}$}

\newcommand\@titlecontents{%
  \newpage
  \setlength\parskip{12pt}
  %\emph{3rd URSI AT-AP-RASC, Gran Canaria, 29 May -- 3 June 2022}\hfill
    \emph{3rd URSI AT-AP-RASC, Gran Canaria, 29 May -- 3 June 2022 \\ \textcolor{red}{\textcopyright 2022 IEEE. Personal use of this material is permitted, but republication/redistribution requires IEEE permission. Refer to IEEE Copyright and Publication Rights for more details.\\ Digital Object Identifier (DOI): 10.23919/AT-AP-RASC54737.2022.9814322}}\hfill 
  \raisebox{-8mm}{\includegraphics[width=29mm]{URSIlogo2}}
  \vspace{-1ex}
  \begin{center}%
    {\fontsize{12}{14}\selectfont\bfseries\@title}%
    \par
    {\normalsize%fontsize{10}{12}\selectfont
      \@author\\
      \@affiliation}%
  \end{center}%
  \if@twocolumn
    \vspace{3ex}\mbox{}%
  \else
    \vspace{3ex}%
  \fi
}
\renewcommand\maketitle{\par
  \begingroup
    \if@twocolumn
      \ifnum \col@number=\@ne
        \@titlecontents
      \else
        \twocolumn[\@titlecontents]%
      \fi
    \else
      \global\@topnum\z@   % Prevents figures from going at top of page.
      \@titlecontents
    \fi
  \endgroup
}