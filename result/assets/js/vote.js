document.addEventListener("DOMContentLoaded", function () {
    console.log("vote.js 로드됨");

    function submitVote(choice) {
        console.log(choice + " 선택됨!");  // 디버깅용 로그
        fetch("http://localhost:5000/vote", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ choice: choice })
        })
        .then(response => response.json())
        .then(data => {
            console.log("서버 응답:", data);  // 디버깅용 로그
            alert(choice + " 투표 완료!");
            updateResults();
        })
        .catch(error => console.error("Error:", error));
    }

    function updateResults() {
        fetch("http://localhost:5000/results")
        .then(response => response.json())
        .then(data => {
            document.getElementById("resultTteokbokki").textContent = `떡볶이: ${data["떡볶이"].toFixed(1)}%`;
            document.getElementById("resultChicken").textContent = `치킨: ${data["치킨"].toFixed(1)}%`;
        })
        .catch(error => console.error("Error fetching results:", error));
    }

    // 버튼 이벤트 추가
    document.getElementById("btnradio1").addEventListener("click", function () {
        submitVote("떡볶이");
        this.disabled = true;
        document.getElementById("btnradio2").disabled = true;
    });

    document.getElementById("btnradio2").addEventListener("click", function () {
        submitVote("치킨");
        this.disabled = true;
        document.getElementById("btnradio1").disabled = true;
    });

    updateResults();  // 페이지 로드 시 결과 업데이트
});
