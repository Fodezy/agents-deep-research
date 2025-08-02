from dataclasses import dataclass


@dataclass
class ChunkInfo:
    text: str
    token_count: int
    start_offset: int
    end_offset: int
    chunk_id: int
    
    def __post_init__(self):
        if self.token_count <= 0:
            raise ValueError("Token count must be positive")
        if self.start_offset < 0:
            raise ValueError("Start offset cannot be negative")
        if self.end_offset <= self.start_offset:
            raise ValueError("End offset must be greater than start offset")
        if self.chunk_id < 0:
            raise ValueError("Chunk ID cannot be negative")