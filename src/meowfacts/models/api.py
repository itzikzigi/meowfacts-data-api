"""Wire shapes returned by the meowfacts HTTP API.

These models exist only to parse and validate responses from the external API.
They are not the output contract — anything we write to disk lives in
`dataset.py`. Keeping the two separated means a breaking change upstream
cannot silently deform our output schema.
"""

from pydantic import BaseModel


class ApiFactResponse(BaseModel):
    data: list[str]


class LanguageOption(BaseModel):
    locale_code: str
    iso_code: str
    full_code: str
    local_name: str
    english_name: str
    full_name: str
    fact_count: int


class ApiOptionsResponse(BaseModel):
    lang: list[LanguageOption]

    def get_languages(self) -> list[str]:
        return [opt.full_code for opt in self.lang]
