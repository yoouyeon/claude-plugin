# 언어 매핑

`prep`·`done`·`docs`가 공유하는 표다. 사용자가 적은 언어 이름을 LeetCode `langSlug`, 파일 확장자, 주석 문법, 마크다운 코드 펜스 태그로 옮긴다.

| 사용자 표기 | langSlug | 확장자 | 줄 주석 | 블록 주석 | 펜스 태그 |
|---|---|---|---|---|---|
| typescript | `typescript` | `.ts` | `//` | `/* */` | `ts` |
| javascript | `javascript` | `.js` | `//` | `/* */` | `js` |
| python | `python3` | `.py` | `#` | `""" """` | `py` |
| java | `java` | `.java` | `//` | `/* */` | `java` |
| c++ | `cpp` | `.cpp` | `//` | `/* */` | `cpp` |
| c | `c` | `.c` | `//` | `/* */` | `c` |
| c# | `csharp` | `.cs` | `//` | `/* */` | `csharp` |
| go | `golang` | `.go` | `//` | `/* */` | `go` |
| rust | `rust` | `.rs` | `//` | `/* */` | `rust` |
| kotlin | `kotlin` | `.kt` | `//` | `/* */` | `kotlin` |
| swift | `swift` | `.swift` | `//` | `/* */` | `swift` |
| ruby | `ruby` | `.rb` | `#` | `=begin =end` | `rb` |

`langSlug`는 사람이 쓰는 이름과 다르다. `python`은 Python 2이므로 Python 3는 `python3`, `go`는 `golang`, `c#`은 `csharp`, `c++`는 `cpp`다.

표에 없는 언어를 사용자가 적으면 `langSlug`는 적힌 값을 그대로 시도하고, 확장자·주석 문법·펜스 태그는 사용자에게 묻는다.

## 재풀이 접미사가 붙는 자리

한 파일에 풀이를 누적할 때, 새 풀이가 도입하는 모든 이름에 같은 순번 접미사를 붙인다. 어느 이름에 붙는지는 언어 계열이 정한다.

| 계열 | 예 | 접미사가 붙는 자리 |
|---|---|---|
| 클래스가 껍데기 | `class Solution` (C++/Java/Python/C#) | 클래스 이름 → `Solution2` |
| 맨몸 함수 | `func`(Go), `function`(TS/JS), `int*`(C) | 함수 이름 → `spiralOrder2` |
| `impl` 블록 | `impl Solution` (Rust) | 메서드 이름 → `spiral_order_2` |
| 클래스가 곧 답 | `LRUCache` 같은 설계 문제 | 클래스 이름 → `LRUCache2` |

Rust의 `impl Solution`은 선언이 아니라 LeetCode가 따로 정의해 둔 타입에 대한 참조다. `impl Solution2`로 바꾸면 존재하지 않는 타입이라 컴파일이 깨진다.
