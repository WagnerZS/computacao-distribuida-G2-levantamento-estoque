class LeitorParser:
    def feed_line(self, line: str) -> bool:
        return line.strip() == "1"
