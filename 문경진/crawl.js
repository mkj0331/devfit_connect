async function fetchEmploymentQuestions(employmentResumeId) {
  const res = await fetch(
    "https://jasoseol.com/employment/employment_question.json",
    {
      method: "POST",
      credentials: "include", // ⭐ 핵심
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        employment_resume_id: employmentResumeId
      })
    }
  );

  const data = await res.json();
  return data.employment_question;
}

const questions = await fetchEmploymentQuestions(410149);
console.log(questions);
