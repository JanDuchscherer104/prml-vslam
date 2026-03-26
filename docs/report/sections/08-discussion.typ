= Discussion

The main risks are method-specific environment complexity, custom data capture quality, and scale
consistency when comparing dense outputs against ARCore or reference reconstructions. These risks
should be documented early because they directly affect benchmark fairness and reproducibility.

The current repository scaffold addresses these risks by separating lightweight project code from
heavy external tools, keeping weekly reporting templates in the repo, and defining a stable work
package split before deeper implementation work begins.
