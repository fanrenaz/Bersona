from abc import ABC, abstractmethod
from datetime import date


class BaseKernel(ABC):
    """
    Abstract base class for all kernels.
    Each kernel is responsible for calculating a specific set of persona traits.
    """

    @abstractmethod
    def calculate(self, birth_date: date, birth_time: "time | None" = None, location: "tuple[float, float] | None" = None) -> dict:
        """
        Calculates the persona traits based on the provided birth date and other optional parameters.

        :param birth_date: The birth date of the user.
        :param birth_time: The birth time of the user.
        :param location: The birth location (latitude, longitude) of the user.
        :return: A dictionary containing the calculated traits.
        """
        pass
