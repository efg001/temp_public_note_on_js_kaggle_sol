# Project Overview

## Summary

The provided dataset appears to be smoothed, potentially using Exponential Moving Average (EMA). This smoothing makes temporal models less attractive because the features of a given timestamp already incorporate information from previous timestamps, preventing the separation of information.

For tabular data, model selection generally does  [not significantly impact performance](https://arxiv.org/pdf/2305.02997) so I decided to start with a simple Multi-Layer Perceptron (MLP). 

**Note:** This model is not yet tuned (512 is a randomly chosen number for the hidden state), and the attached code snippet is only a representation of what I currently have for sharing(actual script have more debugging/training stat monitoring hook and todo comment for myself)

## Details

### Initialization
- **Zero Initialization:** Both input and hidden layer weights are initialized to zero.
- **R² Metric:** The competition uses R² as the evaluation metric. A prediction of zero yields an R² score of zero. Given the nature of the data, it is unavoidable for some days/batches—especially with an undertrained model—to make predictions that result in a negative score. Zero initialization helps the model find the baseline again.

### Network Configuration
- **Avoiding Vanishing Gradients:** Without using gain (Xavier/Kaiming initialization), the network can suffer from vanishing gradients because activation functions shrink the variances of the output. However, with the right learning rate schedule and the Adam optimizer, the model converges reasonably well.
- **ReLU Activation:** At the start of training, using ReLU with a uniformly sampled random bias causes the output layer to produce results very close to zero, which serves as a desired baseline and does not prevent the model from learning.

### Model Architecture
- **Multivariable Responder Regression:** Added an MLP for multivariable responder regression, taking the last hidden state as a feature.
- **Responder Prediction MLP:** Added an MLP for predicting all responders, utilizing the last hidden state as a PLS/PCA-like transformed feature that captures information from other responders to predict the scored responder. Although an autoencoder is a more straightforward solution, the last competition’s winning solution used it, so I opted to explore an alternative approach.

### Data Handling
- **Gapped Batching:** 
  - **Issue:** The features and targets are suspected to be smoothed with EMA (due to strong correlation between intraday lagged features and responders). Feeding continuous batches encourages the model to leverage leakage from the previous batch.
  - **Solution:** Instead of batching inputs sequentially (e.g., 1–batch size, batch size+1–batch size*2), use gapped batching such as 1–batch size, batch size*2–batch size*3, etc. This reduces leakage by ensuring that consecutive batches do not overlap in a way that allows the model to exploit smoothed information from previous batches.

- **Data Cleaning:**
  - **Sample Removal:** Removed 4 out of 250 days' worth of samples for each symbol.
  - **Clipping Instead of Standard Scaling:** Instead of standard scaling, applied clipping to handle outliers.
  - **Earnings Date Handling:** It is suspected that the data is not thoroughly cleaned for modeling purposes. To account for potential earnings dates where intraday technical indicator-based models should handle data differently, one day per quarter was removed. This avoids large losses that could penalize the model for factors it does not have information to predict.

## Future Work
- **Model Tuning:** The current MLP model uses a randomly chosen hidden state size of 512. Future work includes tuning this hyperparameter for optimal performance.
- **Alternative Architectures:** Exploring other model architectures beyond MLPs to potentially improve performance despite the smoothed nature of the dataset.

## References
- [Model Selection in Tabular Data](https://arxiv.org/pdf/2305.02997)

