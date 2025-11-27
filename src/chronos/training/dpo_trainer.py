"""Direct Preference Optimization (DPO) trainer for Chronos agent."""

import torch
from typing import Dict, Any, List, Optional
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from trl import DPOTrainer as TRLDPOTrainer
from datasets import Dataset

from src.chronos.config import config
from src.chronos.utils.logger import get_logger

logger = get_logger(__name__)


class DPOTrainer:
    """
    Trainer for Direct Preference Optimization of scheduling preferences.
    
    DPO fine-tunes the model to align with user preferences without
    requiring a reward model or complex RL setup.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        output_dir: str = "./models/dpo_checkpoints"
    ):
        """
        Initialize DPO trainer.
        
        Args:
            model_name: Base model name
            output_dir: Directory to save checkpoints
        """
        self.model_name = model_name or config.model.name
        self.output_dir = output_dir
        self.model = None
        self.tokenizer = None
        self.ref_model = None
    
    def load_model(self) -> None:
        """Load base model and reference model for DPO."""
        logger.info(f"Loading model: {self.model_name}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            token=config.hf_token,
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load model for training
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            token=config.hf_token,
        )
        
        # Load reference model (frozen copy)
        self.ref_model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            token=config.hf_token,
        )
        
        logger.info("Models loaded successfully")
    
    def prepare_dataset(
        self,
        preference_data: List[Dict[str, Any]]
    ) -> Dataset:
        """
        Prepare preference dataset for DPO training.
        
        Expected format for each example:
        {
            "prompt": "...",  # User request
            "chosen": "...",  # Preferred response
            "rejected": "..."  # Rejected response
        }
        
        Args:
            preference_data: List of preference examples
            
        Returns:
            HuggingFace Dataset
        """
        logger.info(f"Preparing dataset with {len(preference_data)} examples")
        
        # Validate data
        required_keys = {"prompt", "chosen", "rejected"}
        for example in preference_data:
            if not required_keys.issubset(example.keys()):
                raise ValueError(f"Example missing required keys: {required_keys}")
        
        return Dataset.from_list(preference_data)
    
    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Optional[Dataset] = None,
    ) -> None:
        """
        Train model using DPO.
        
        Args:
            train_dataset: Training dataset
            eval_dataset: Evaluation dataset
        """
        if self.model is None:
            self.load_model()
        
        logger.info("Starting DPO training...")
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=config.dpo.epochs,
            per_device_train_batch_size=config.dpo.batch_size,
            gradient_accumulation_steps=config.dpo.gradient_accumulation_steps,
            learning_rate=config.dpo.learning_rate,
            warmup_steps=config.dpo.warmup_steps,
            logging_steps=config.dpo.logging_steps,
            save_steps=config.dpo.save_steps,
            eval_steps=config.dpo.eval_steps if eval_dataset else None,
            evaluation_strategy="steps" if eval_dataset else "no",
            save_total_limit=3,
            fp16=True,
            remove_unused_columns=False,
            report_to=["tensorboard"],
        )
        
        # Initialize DPO trainer
        dpo_trainer = TRLDPOTrainer(
            model=self.model,
            ref_model=self.ref_model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            beta=config.dpo.beta,
            max_length=config.dpo.max_length,
            max_prompt_length=config.dpo.max_prompt_length,
        )
        
        # Train
        dpo_trainer.train()
        
        logger.info("Training complete!")
        
        # Save final model
        self.save_model()
    
    def save_model(self, path: Optional[str] = None) -> None:
        """Save trained model."""
        save_path = path or f"{self.output_dir}/final"
        
        logger.info(f"Saving model to: {save_path}")
        
        self.model.save_pretrained(save_path)
        self.tokenizer.save_pretrained(save_path)
        
        logger.info("Model saved successfully")


def create_example_preferences() -> List[Dict[str, Any]]:
    """
    Create example preference data for DPO training.
    
    This demonstrates the format needed for training. In production,
    collect real user feedback on scheduling decisions.
    
    Returns:
        List of preference examples
    """
    examples = [
        {
            "prompt": "Schedule a team meeting for next week",
            "chosen": "I've found Tuesday at 2 PM works best. This gives everyone preparation time and avoids the Monday rush. Would you like me to send invitations?",
            "rejected": "How about Monday at 8 AM? I know it's early but we can get it done first thing.",
        },
        {
            "prompt": "Find time for a 1-on-1 with my manager",
            "chosen": "I recommend Thursday at 3 PM. This allows time for weekly prep and gives you both flexibility if needed. Duration: 30 minutes.",
            "rejected": "I can squeeze you in for 15 minutes on Friday at 5:30 PM.",
        },
        {
            "prompt": "Schedule client demo",
            "chosen": "Wednesday at 10 AM is ideal for client presentations - mid-week, mid-morning when attention is high. I'll block 60 minutes plus 15-minute buffer.",
            "rejected": "Friday at 4 PM is available.",
        },
        {
            "prompt": "Book time for deep work",
            "chosen": "I've reserved Tuesday and Thursday mornings (9-11 AM) for focused work. These blocks are protected and I'll decline conflicting meetings automatically.",
            "rejected": "You have 20 minutes free between meetings on Wednesday.",
        },
        {
            "prompt": "Reschedule tomorrow's 9 AM meeting",
            "chosen": "I've found three options: 1) Same day at 2 PM, 2) Thursday at 9 AM (same time, different day), 3) Friday at 10 AM. Which works best?",
            "rejected": "I can move it to 8 AM tomorrow if you want to keep the same day.",
        },
    ]
    
    return examples


if __name__ == "__main__":
    # Example usage
    trainer = DPOTrainer()
    
    # Create example preference data
    preferences = create_example_preferences()
    
    # Prepare dataset
    dataset = trainer.prepare_dataset(preferences)
    
    # Train (in practice, you'd have a larger dataset)
    # trainer.train(dataset)
    
    logger.info("DPO trainer ready. Collect user preferences and run training!")

