from abc import ABC, abstractmethod
from datetime import date


class BaseKernel(ABC):
    """
    Abstract base class for all kernels.
    Each kernel is responsible for calculating a specific set of persona traits.
    """

    @abstractmethod
    def calculate(self, birth_date: date, **kwargs) -> dict:
        """
        Calculates the persona traits based on the provided birth date and other optional parameters.

        :param birth_date: The birth date of the user.
        :param kwargs: Additional optional parameters (e.g., birth_time, location).
        :return: A dictionary containing the calculated traits.
        """
        pass
