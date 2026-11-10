# 지금 열린 쉼터

서울 무더위쉼터를 "누가, 언제, 어디서" 갈 수 있는지 보여 주는 웹앱입니다. 공간과행태 기말 프로젝트(3팀).

**보기:** 저장소의 GitHub Pages 주소 (Settings > Pages 에 표시)

## 자동 갱신

`.github/workflows/update.yml` 이 매시 7분에 `update.py` 를 실행해 서울 열린데이터광장 실시간 API 세 개를 불러오고, `index.html` 안의 데이터를 바꿔 다시 배포합니다.

| 화면에 보이는 것 | API | 갱신 주기(원자료) |
|---|---|---|
| 우리 동네 지금 기온 | S-DoT 환경정보 `sDoTEnv` | 1시간 |
| 지금 붐비는 곳, 오늘 혼잡도 예측 | 실시간 도시데이터 `citydata` | 5분 |
| 지금 대기질 | 권역별 실시간 대기환경 `RealtimeCityAir`, 평균 `ListAvgOfSeoulAirQualityService` | 1시간 |

인증키는 Settings > Secrets and variables > Actions 의 `SEOUL_API_KEY` 에 넣습니다. 코드에는 들어 있지 않습니다.

쉼터·생활인구·저녁 기온 등 분석 자료는 HTML 안에 고정되어 있고, 바탕지도·건물 정보·사진은 열 때 OpenStreetMap, Esri, 위키미디어에서 불러옵니다.
